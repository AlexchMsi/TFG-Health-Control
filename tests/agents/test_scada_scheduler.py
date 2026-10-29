import sys
import types

from tests.agents.collectors.import_helpers import ROOT, load_module


class FakeBackgroundScheduler:
    def __init__(self, timezone=None):
        self.jobs = {}

    def add_job(self, **kwargs):
        self.jobs[kwargs["id"]] = kwargs

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def remove_job(self, job_id):
        self.jobs.pop(job_id)

    def start(self):
        pass

    def shutdown(self, wait=False):
        pass


class FakeIntervalTrigger:
    def __init__(self, seconds, jitter=None):
        self.seconds = seconds
        self.jitter = jitter


class FakeWriter:
    def __init__(self):
        self.points = []

    def write_point(self, **kwargs):
        self.points.append(kwargs)


def test_add_target_schedules_scada_job(monkeypatch):
    background = types.ModuleType("apscheduler.schedulers.background")
    background.BackgroundScheduler = FakeBackgroundScheduler
    interval = types.ModuleType("apscheduler.triggers.interval")
    interval.IntervalTrigger = FakeIntervalTrigger
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.background", background)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.interval", interval)
    writer_module = types.ModuleType("shared.influx.writer")
    writer_module.InfluxWriter = object
    monkeypatch.setitem(sys.modules, "shared.influx.writer", writer_module)

    module = load_module("scheduler", ROOT / "agents" / "scada-agent" / "src" / "scheduler.py", "scada_src")
    scheduler = module.AgentScheduler(FakeWriter())
    scheduler.add_target({"id": "s1", "config": {"opcua_url": "opc.tcp://host:4840", "tags": [], "poll_interval_seconds": 12}})

    job = scheduler.aps.jobs["scada_s1"]
    assert job["args"][0].source_id == "s1"
    assert job["max_instances"] == 1
    assert job["replace_existing"] is True
    assert job["trigger"].seconds == 12
    assert job["trigger"].jitter == 5


def test_write_uses_influx_writer_and_reachable_int(monkeypatch):
    background = types.ModuleType("apscheduler.schedulers.background")
    background.BackgroundScheduler = FakeBackgroundScheduler
    interval = types.ModuleType("apscheduler.triggers.interval")
    interval.IntervalTrigger = FakeIntervalTrigger
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.background", background)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.interval", interval)
    writer_module = types.ModuleType("shared.influx.writer")
    writer_module.InfluxWriter = object
    monkeypatch.setitem(sys.modules, "shared.influx.writer", writer_module)

    module = load_module("scheduler", ROOT / "agents" / "scada-agent" / "src" / "scheduler.py", "scada_src")
    writer = FakeWriter()
    scheduler = module.AgentScheduler(writer)
    metric = module.ScadaTagMetric(source_id="s1", source_type="scada", scada_type="Ignition", tag_name="Temp", reachable=True, quality="GOOD", value_float=1.0)

    scheduler._write(metric)

    assert writer.points[0]["measurement"] == "scada_tag_health"
    assert writer.points[0]["tags"] == {"source_id": "s1", "scada_type": "Ignition", "tag_name": "Temp"}
    assert writer.points[0]["fields"]["reachable"] == 1
