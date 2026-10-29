import sys
import types

import pytest

from shared.models.siemens import SiemensPlcMetric
from tests.agents.collectors.import_helpers import load_module, siemens_agent_path


class FakeIntervalTrigger:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeBackgroundScheduler:
    def __init__(self, timezone):
        self.timezone = timezone
        self.jobs = []
        self.removed = []

    def add_job(self, **kwargs):
        self.jobs.append(kwargs)

    def get_job(self, job_id):
        return next((job for job in self.jobs if job["id"] == job_id), None)

    def remove_job(self, job_id):
        self.removed.append(job_id)

    def start(self):
        pass

    def shutdown(self, wait):
        pass


class FakeWriter:
    def __init__(self):
        self.points = []
        self.fail = False

    def write_point(self, **kwargs):
        if self.fail:
            raise RuntimeError("boom")
        self.points.append(kwargs)


@pytest.fixture
def scheduler_module(monkeypatch):
    background = types.ModuleType("apscheduler.schedulers.background")
    interval = types.ModuleType("apscheduler.triggers.interval")
    background.BackgroundScheduler = FakeBackgroundScheduler
    interval.IntervalTrigger = FakeIntervalTrigger
    monkeypatch.setitem(sys.modules, "apscheduler", types.ModuleType("apscheduler"))
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers", types.ModuleType("apscheduler.schedulers"))
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.background", background)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", types.ModuleType("apscheduler.triggers"))
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.interval", interval)
    writer = types.ModuleType("shared.influx.writer")
    writer.InfluxWriter = object
    monkeypatch.setitem(sys.modules, "shared.influx.writer", writer)
    pkg = "siemens_agent_scheduler"
    collectors_pkg = types.ModuleType(f"{pkg}.collectors")
    collectors_pkg.__path__ = []
    opcua = types.ModuleType(f"{pkg}.collectors.opcua_collector")
    snap7 = types.ModuleType(f"{pkg}.collectors.snap7_collector")
    opcua.OpcuaCollector = object
    snap7.Snap7Collector = object
    monkeypatch.setitem(sys.modules, f"{pkg}.collectors", collectors_pkg)
    monkeypatch.setitem(sys.modules, f"{pkg}.collectors.opcua_collector", opcua)
    monkeypatch.setitem(sys.modules, f"{pkg}.collectors.snap7_collector", snap7)
    return load_module("scheduler", siemens_agent_path("scheduler.py"), "siemens_agent_scheduler")


def test_add_target_schedules_job_with_method_and_interval(scheduler_module):
    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    target = {"id": "plc1", "config": {"collection_method": "snap7", "poll_interval_seconds": 12}}

    scheduler.add_target(target)

    job = scheduler.aps.jobs[0]
    assert job["func"] == scheduler._collect_and_write
    assert job["id"] == "plc1"
    assert job["args"] == [target, "snap7"]
    assert job["max_instances"] == 1
    assert job["misfire_grace_time"] == 12
    assert job["replace_existing"] is True
    assert job["trigger"].kwargs == {"seconds": 12, "jitter": 5}


def test_collect_auto_returns_no_method_metric_when_unconfigured(scheduler_module):
    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    target = {"id": "plc1", "display_name": "PLC 1", "plant": "Madrid", "config": {}}

    metric = scheduler._collect(target, "auto")

    assert isinstance(metric, SiemensPlcMetric)
    assert metric.source_id == "plc1"
    assert metric.reachable is False
    assert metric.last_error_text == "No valid collection method configured"


def _fake_collector_cls(metric):
    class _FakeCollector:
        def __init__(self, target):
            self.target = target

        def collect(self):
            return metric

    return _FakeCollector


def test_auto_no_fallback_when_opcua_connected_but_cpu_stopped(scheduler_module, monkeypatch):
    opcua_metric = SiemensPlcMetric(
        source_id="plc1", source_type="siemens_plc", reachable=True, cpu_state="STOP"
    )
    opcua_mod = sys.modules["siemens_agent_scheduler.collectors.opcua_collector"]
    snap7_mod = sys.modules["siemens_agent_scheduler.collectors.snap7_collector"]
    monkeypatch.setattr(opcua_mod, "OpcuaCollector", _fake_collector_cls(opcua_metric))

    class _ExplodingSnap7:
        def __init__(self, target):
            raise AssertionError("Snap7 fallback must not run for a reachable PLC in STOP")

    monkeypatch.setattr(snap7_mod, "Snap7Collector", _ExplodingSnap7)

    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    target = {
        "id": "plc1",
        "display_name": "PLC 1",
        "plant": "Madrid",
        "config": {"opcua_url": "opc.tcp://plc:4840", "snap7_host": "10.0.0.1"},
    }

    metric = scheduler._collect(target, "auto")

    assert metric is opcua_metric
    assert metric.reachable is True
    assert metric.cpu_state == "STOP"


def test_auto_falls_back_to_snap7_when_opcua_connection_fails(scheduler_module, monkeypatch):
    opcua_metric = SiemensPlcMetric(
        source_id="plc1", source_type="siemens_plc", reachable=False, last_error_text="connect failed"
    )
    snap7_metric = SiemensPlcMetric(
        source_id="plc1", source_type="siemens_plc", reachable=True, cpu_state="RUN",
        collection_method="snap7",
    )
    opcua_mod = sys.modules["siemens_agent_scheduler.collectors.opcua_collector"]
    snap7_mod = sys.modules["siemens_agent_scheduler.collectors.snap7_collector"]
    monkeypatch.setattr(opcua_mod, "OpcuaCollector", _fake_collector_cls(opcua_metric))
    monkeypatch.setattr(snap7_mod, "Snap7Collector", _fake_collector_cls(snap7_metric))

    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    target = {
        "id": "plc1",
        "display_name": "PLC 1",
        "plant": "Madrid",
        "config": {"opcua_url": "opc.tcp://plc:4840", "snap7_host": "10.0.0.1"},
    }

    metric = scheduler._collect(target, "auto")

    assert metric is snap7_metric
    assert metric.collection_method == "snap7"


def test_write_siemens_metric_converts_optional_bools(scheduler_module):
    writer = FakeWriter()
    scheduler = scheduler_module.AgentScheduler(writer)
    metric = SiemensPlcMetric(
        source_id="plc1",
        source_type="siemens_plc",
        plc_name="PLC 1",
        plant="Madrid",
        reachable=False,
        battery_ok=True,
        last_error_code=7,
        last_error_text="fault",
    )

    scheduler._write(metric)

    point = writer.points[0]
    assert point["measurement"] == "siemens_plc_health"
    assert point["tags"]["source_id"] == "plc1"
    # Empty model/firmware must become a placeholder (empty tags are dropped
    # by the InfluxDB client and would break the API's pivot).
    assert point["tags"]["model"] == "unknown"
    assert point["tags"]["firmware"] == "unknown"
    assert point["fields"]["reachable"] == 0
    assert point["fields"]["battery_ok"] == 1
    assert point["fields"]["last_error_code"] == 7
    assert point["fields"]["last_error_text"] == "fault"


def test_write_swallows_writer_errors(scheduler_module):
    writer = FakeWriter()
    writer.fail = True
    scheduler = scheduler_module.AgentScheduler(writer)

    scheduler._write(SiemensPlcMetric(source_id="plc1", source_type="siemens_plc"))
