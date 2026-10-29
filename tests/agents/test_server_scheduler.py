import sys
import types
from datetime import datetime, timezone

import pytest

from shared.models.server import DiskMetric, ServiceStatus, WindowsServerMetric
from shared.models.vmware import ESXiHostMetric, VMMetric
from tests.agents.collectors.import_helpers import load_module, server_agent_path


class FakeIntervalTrigger:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeBackgroundScheduler:
    def __init__(self, timezone):
        self.timezone = timezone
        self.jobs = []
        self.removed = []
        self.started = False
        self.shutdown_wait = None

    def add_job(self, **kwargs):
        self.jobs.append(kwargs)

    def get_job(self, job_id):
        return next((job for job in self.jobs if job["id"] == job_id), None)

    def remove_job(self, job_id):
        self.removed.append(job_id)

    def start(self):
        self.started = True

    def shutdown(self, wait):
        self.shutdown_wait = wait


class FakeCollector:
    def __init__(self, cfg):
        self.cfg = cfg
        self.metrics = []

    def collect(self):
        return self.metrics


class FakeWriteError(Exception):
    pass


class FakeWriter:
    def __init__(self):
        self.points = []
        self.fail = False

    def write_point(self, **kwargs):
        if self.fail:
            raise FakeWriteError("boom")
        self.points.append(kwargs)


@pytest.fixture
def scheduler_module(monkeypatch):
    apscheduler = types.ModuleType("apscheduler")
    schedulers = types.ModuleType("apscheduler.schedulers")
    background = types.ModuleType("apscheduler.schedulers.background")
    triggers = types.ModuleType("apscheduler.triggers")
    interval = types.ModuleType("apscheduler.triggers.interval")
    background.BackgroundScheduler = FakeBackgroundScheduler
    interval.IntervalTrigger = FakeIntervalTrigger

    pkg = "server_agent_scheduler"
    collectors_pkg = types.ModuleType(f"{pkg}.collectors")
    collectors_pkg.__path__ = []
    base = types.ModuleType(f"{pkg}.collectors.base")
    snmp = types.ModuleType(f"{pkg}.collectors.windows_snmp")
    winrm = types.ModuleType(f"{pkg}.collectors.windows_winrm")
    vmware = types.ModuleType(f"{pkg}.collectors.vmware")
    base.AbstractCollector = object
    snmp.WindowsSNMPCollector = FakeCollector
    winrm.WindowsWinRMCollector = FakeCollector
    vmware.VMwareCollector = FakeCollector

    writer = types.ModuleType("shared.influx.writer")
    writer.InfluxWriter = object
    writer.WriteError = FakeWriteError

    for name, module in {
        "apscheduler": apscheduler,
        "apscheduler.schedulers": schedulers,
        "apscheduler.schedulers.background": background,
        "apscheduler.triggers": triggers,
        "apscheduler.triggers.interval": interval,
        f"{pkg}.collectors": collectors_pkg,
        f"{pkg}.collectors.base": base,
        f"{pkg}.collectors.windows_snmp": snmp,
        f"{pkg}.collectors.windows_winrm": winrm,
        f"{pkg}.collectors.vmware": vmware,
        "shared.influx.writer": writer,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)

    return load_module("scheduler", server_agent_path("scheduler.py"), pkg)


def test_add_target_schedules_windows_job_with_flat_config(scheduler_module):
    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    target = {
        "id": "srv1",
        "config": {"host": "10.0.0.1", "collection_method": "winrm", "poll_interval_seconds": 42},
    }

    scheduler.add_target(target)

    job = scheduler.aps.jobs[0]
    assert job["func"] == scheduler._run_collection
    assert job["id"] == "windows_srv1"
    assert job["max_instances"] == 1
    assert job["misfire_grace_time"] == 42
    assert job["replace_existing"] is True
    assert job["trigger"].kwargs == {"seconds": 42, "jitter": 5}
    assert job["args"][0].cfg == {"id": "srv1", "host": "10.0.0.1", "collection_method": "winrm", "poll_interval_seconds": 42}


def test_remove_target_only_removes_existing_job(scheduler_module):
    scheduler = scheduler_module.AgentScheduler(FakeWriter())
    scheduler.add_target({"id": "srv1", "config": {}})

    scheduler.remove_target("missing")
    scheduler.remove_target("srv1")

    assert scheduler.aps.removed == ["windows_srv1"]


def test_run_collection_writes_all_supported_metrics_and_int_bools(scheduler_module):
    writer = FakeWriter()
    scheduler = scheduler_module.AgentScheduler(writer)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    collector = types.SimpleNamespace(collect=lambda: [
        WindowsServerMetric(
            source_id="srv1",
            source_type="windows_server",
            collected_at=ts,
            hostname="srv1",
            reachable=True,
            disks=[DiskMetric("C:", 100, 50, 50)],
            services=[ServiceStatus("W32Time", "Windows Time", "Running", "Auto")],
        ),
        ESXiHostMetric(source_id="esx1", source_type="esxi_host", collected_at=ts, hostname="esx1", maintenance_mode=True, reachable=False),
        VMMetric(source_id="vm1", source_type="vm", collected_at=ts, vm_name="vm1", power_state="poweredOn", reachable=True),
    ])

    scheduler._run_collection(collector)

    assert [point["measurement"] for point in writer.points] == [
        "server_health", "disk_health", "service_health", "esxi_health", "vm_health"
    ]
    assert writer.points[0]["fields"]["reachable"] == 1
    assert writer.points[2]["fields"]["is_running"] == 1
    assert writer.points[3]["fields"]["maintenance_mode"] == 1
    assert writer.points[3]["fields"]["reachable"] == 0
    assert writer.points[4]["fields"]["is_powered_on"] == 1


def test_write_esxi_includes_last_error_text_only_when_set(scheduler_module):
    writer = FakeWriter()
    scheduler = scheduler_module.AgentScheduler(writer)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

    scheduler._write_esxi(
        ESXiHostMetric(
            source_id="esxi-vc.local", source_type="esxi_host", collected_at=ts,
            hostname="vc.local", reachable=False, last_error_text="connection refused",
        ),
        ts,
    )
    scheduler._write_esxi(
        ESXiHostMetric(
            source_id="esxi-host-1", source_type="esxi_host", collected_at=ts,
            hostname="esxi01", reachable=True,
        ),
        ts,
    )

    failed, ok = writer.points
    assert failed["fields"]["reachable"] == 0
    assert failed["fields"]["last_error_text"] == "connection refused"
    assert ok["fields"]["reachable"] == 1
    assert "last_error_text" not in ok["fields"]


def test_run_collection_continues_after_write_error(scheduler_module):
    writer = FakeWriter()
    writer.fail = True
    scheduler = scheduler_module.AgentScheduler(writer)
    metric = WindowsServerMetric(source_id="srv1", source_type="windows_server")

    scheduler._run_collection(types.SimpleNamespace(collect=lambda: [metric]))
