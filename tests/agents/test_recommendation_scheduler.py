import sys
import types

import pytest

from tests.agents.collectors.import_helpers import load_module, recommendation_agent_path


class FakeIntervalTrigger:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeBlockingScheduler:
    def __init__(self, timezone):
        self.timezone = timezone
        self.jobs = []
        self.started = False

    def add_job(self, **kwargs):
        self.jobs.append(kwargs)

    def start(self):
        self.started = True

    def shutdown(self, wait):
        pass


class FakeReader:
    def get_latest_metrics(self):
        return {"scada_tag_health": [{"source_id": "tag1"}]}


class FakeOllama:
    def __init__(self, raw):
        self.raw = raw
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.raw


@pytest.fixture
def scheduler_module(monkeypatch):
    blocking = types.ModuleType("apscheduler.schedulers.blocking")
    interval = types.ModuleType("apscheduler.triggers.interval")
    blocking.BlockingScheduler = FakeBlockingScheduler
    interval.IntervalTrigger = FakeIntervalTrigger
    monkeypatch.setitem(sys.modules, "apscheduler", types.ModuleType("apscheduler"))
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers", types.ModuleType("apscheduler.schedulers"))
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.blocking", blocking)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", types.ModuleType("apscheduler.triggers"))
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.interval", interval)
    influx = types.ModuleType("influxdb_client")
    influx.InfluxDBClient = object
    httpx = types.ModuleType("httpx")
    httpx.HTTPError = Exception
    monkeypatch.setitem(sys.modules, "influxdb_client", influx)
    monkeypatch.setitem(sys.modules, "httpx", httpx)
    package = "recommendation_agent"
    load_module("prompt_builder", recommendation_agent_path("prompt_builder.py"), package)
    return load_module("scheduler", recommendation_agent_path("scheduler.py"), package)


def test_analyze_stores_parsed_recommendation(scheduler_module, tmp_path):
    output = tmp_path / "recommendations.json"
    scheduler = scheduler_module.RecommendationScheduler(
        FakeReader(),
        FakeOllama('{"summary":"ok","risk_level":"low","recommendations":[]}'),
        15,
        str(output),
    )

    result = scheduler.analyze()

    assert result["summary"] == "ok"
    assert "generated_at" in result
    assert output.exists()


def test_analyze_falls_back_on_invalid_json(scheduler_module, tmp_path):
    scheduler = scheduler_module.RecommendationScheduler(FakeReader(), FakeOllama("texto"), 15, str(tmp_path / "r.json"))

    result = scheduler.analyze()

    assert result["risk_level"] == "medium"
    assert result["recommendations"][0]["finding"] == "texto"


def test_start_schedules_blocking_job(scheduler_module, tmp_path):
    scheduler = scheduler_module.RecommendationScheduler(
        FakeReader(),
        FakeOllama('{"summary":"ok","risk_level":"low","recommendations":[]}'),
        7,
        str(tmp_path / "r.json"),
    )

    scheduler.start()

    job = scheduler._aps.jobs[0]
    assert job["id"] == "recommendation_analysis"
    assert job["func"] == scheduler.run
    assert job["max_instances"] == 1
    assert job["misfire_grace_time"] == 420
    assert job["trigger"].kwargs == {"minutes": 7}
    assert scheduler._aps.started is True


def test_run_swallows_analysis_errors(scheduler_module, tmp_path):
    class FailingReader:
        def get_latest_metrics(self):
            raise RuntimeError("influx down")

    scheduler = scheduler_module.RecommendationScheduler(
        FailingReader(), FakeOllama("{}"), 15, str(tmp_path / "r.json")
    )

    scheduler.run()  # must not raise


def test_write_is_atomic_leaves_no_tmp_file(scheduler_module, tmp_path):
    output = tmp_path / "recommendations.json"
    scheduler = scheduler_module.RecommendationScheduler(
        FakeReader(),
        FakeOllama('{"summary":"ok","risk_level":"low","recommendations":[]}'),
        15,
        str(output),
    )

    scheduler.analyze()

    assert output.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_history_reloaded_on_init(scheduler_module, tmp_path):
    import json

    output = tmp_path / "recommendations.json"
    output.write_text(json.dumps([{"summary": "previo", "risk_level": "low", "recommendations": []}]), encoding="utf-8")
    scheduler = scheduler_module.RecommendationScheduler(
        FakeReader(),
        FakeOllama('{"summary":"nuevo","risk_level":"low","recommendations":[]}'),
        15,
        str(output),
    )

    scheduler.analyze()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert [entry["summary"] for entry in data] == ["nuevo", "previo"]


def test_corrupt_history_is_ignored(scheduler_module, tmp_path):
    output = tmp_path / "recommendations.json"
    output.write_text("{corrupto", encoding="utf-8")

    scheduler = scheduler_module.RecommendationScheduler(
        FakeReader(), FakeOllama("{}"), 15, str(output)
    )

    assert list(scheduler._latest) == []
