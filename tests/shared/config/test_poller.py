import importlib
import sys
import types

import pytest


class FakeIntervalTrigger:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeResponse:
    def __init__(self, targets=None, error=None):
        self._targets = targets or []
        self._error = error

    def raise_for_status(self):
        if self._error:
            raise self._error

    def json(self):
        return self._targets


class FakeRequests(types.ModuleType):
    def __init__(self):
        super().__init__("requests")
        self.responses = []
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.responses.pop(0)


class FakeAgentScheduler:
    def __init__(self):
        self.added = []
        self.removed = []

    def add_target(self, target):
        self.added.append(target)

    def remove_target(self, target_id):
        self.removed.append(target_id)


class FakeApsScheduler:
    def __init__(self):
        self.jobs = []

    def add_job(self, *args, **kwargs):
        self.jobs.append({"args": args, "kwargs": kwargs})


@pytest.fixture
def poller_module(monkeypatch):
    requests = FakeRequests()

    apscheduler = types.ModuleType("apscheduler")
    schedulers = types.ModuleType("apscheduler.schedulers")
    schedulers_base = types.ModuleType("apscheduler.schedulers.base")
    schedulers_base.BaseScheduler = object
    triggers = types.ModuleType("apscheduler.triggers")
    triggers_interval = types.ModuleType("apscheduler.triggers.interval")
    triggers_interval.IntervalTrigger = FakeIntervalTrigger

    monkeypatch.setitem(sys.modules, "requests", requests)
    monkeypatch.setitem(sys.modules, "apscheduler", apscheduler)
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers", schedulers)
    monkeypatch.setitem(sys.modules, "apscheduler.schedulers.base", schedulers_base)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers", triggers)
    monkeypatch.setitem(sys.modules, "apscheduler.triggers.interval", triggers_interval)

    sys.modules.pop("shared.config.poller", None)
    module = importlib.import_module("shared.config.poller")
    module.fake_requests = requests
    return module


def test_start_syncs_immediately_and_registers_periodic_job(poller_module):
    poller_module.fake_requests.responses = [FakeResponse([{"id": "s1", "enabled": True}])]
    scheduler = FakeAgentScheduler()
    aps = FakeApsScheduler()
    poller = poller_module.ConfigPoller("http://api/", "server", scheduler, aps, poll_every=15)

    poller.start()

    assert scheduler.added == [{"id": "s1", "enabled": True}]
    assert poller_module.fake_requests.calls == [
        {"url": "http://api/config/targets", "params": {"agent_type": "server"}, "timeout": 10}
    ]
    assert len(aps.jobs) == 1
    assert aps.jobs[0]["args"] == (poller._sync,)
    assert aps.jobs[0]["kwargs"]["id"] == "config_poller"
    assert aps.jobs[0]["kwargs"]["max_instances"] == 1
    assert aps.jobs[0]["kwargs"]["replace_existing"] is True
    assert aps.jobs[0]["kwargs"]["trigger"].kwargs == {"seconds": 15}


def test_sync_adds_new_enabled_targets_and_removes_missing_or_disabled(poller_module):
    poller_module.fake_requests.responses = [
        FakeResponse([
            {"id": "s1", "enabled": True},
            {"id": "s2", "enabled": True},
        ]),
        FakeResponse([
            {"id": "s1", "enabled": False},
            {"id": "s3", "enabled": True},
        ]),
    ]
    scheduler = FakeAgentScheduler()
    poller = poller_module.ConfigPoller("http://api", "server", scheduler, FakeApsScheduler())

    poller._sync()
    poller._sync()

    assert [target["id"] for target in scheduler.added] == ["s1", "s2", "s3"]
    assert set(scheduler.removed) == {"s1", "s2"}


def test_sync_readds_target_when_updated_at_changes(poller_module):
    old_cfg = {"id": "s1", "enabled": True, "updated_at": "2026-01-01T00:00:00", "config": {"host": "10.0.0.1"}}
    new_cfg = {"id": "s1", "enabled": True, "updated_at": "2026-01-02T00:00:00", "config": {"host": "10.0.0.2"}}
    poller_module.fake_requests.responses = [FakeResponse([old_cfg]), FakeResponse([new_cfg])]
    scheduler = FakeAgentScheduler()
    poller = poller_module.ConfigPoller("http://api", "server", scheduler, FakeApsScheduler())

    poller._sync()
    poller._sync()

    assert len(scheduler.added) == 2
    assert scheduler.added[1]["config"] == {"host": "10.0.0.2"}
    assert scheduler.removed == []


def test_sync_does_not_readd_target_when_updated_at_unchanged(poller_module):
    target = {"id": "s1", "enabled": True, "updated_at": "2026-01-01T00:00:00"}
    poller_module.fake_requests.responses = [FakeResponse([target]), FakeResponse([dict(target)])]
    scheduler = FakeAgentScheduler()
    poller = poller_module.ConfigPoller("http://api", "server", scheduler, FakeApsScheduler())

    poller._sync()
    poller._sync()

    assert len(scheduler.added) == 1


def test_sync_readds_target_after_disable_enable_cycle(poller_module):
    stamp = "2026-01-01T00:00:00"
    poller_module.fake_requests.responses = [
        FakeResponse([{"id": "s1", "enabled": True, "updated_at": stamp}]),
        FakeResponse([{"id": "s1", "enabled": False, "updated_at": stamp}]),
        FakeResponse([{"id": "s1", "enabled": True, "updated_at": stamp}]),
    ]
    scheduler = FakeAgentScheduler()
    poller = poller_module.ConfigPoller("http://api", "server", scheduler, FakeApsScheduler())

    poller._sync()
    poller._sync()
    poller._sync()

    assert [target["id"] for target in scheduler.added] == ["s1", "s1"]
    assert scheduler.removed == ["s1"]


def test_sync_keeps_known_ids_when_fetch_fails(poller_module):
    poller_module.fake_requests.responses = [
        FakeResponse([{"id": "s1", "enabled": True}]),
        FakeResponse(error=RuntimeError("boom")),
    ]
    scheduler = FakeAgentScheduler()
    poller = poller_module.ConfigPoller("http://api", "server", scheduler, FakeApsScheduler())

    poller._sync()
    poller._sync()

    assert [target["id"] for target in scheduler.added] == ["s1"]
    assert scheduler.removed == []
