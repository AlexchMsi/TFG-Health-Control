import sys
import types
from dataclasses import is_dataclass
from types import SimpleNamespace

from tests.agents.collectors.import_helpers import load_module, siemens_collector_path


def _install_snap7():
    snap7 = types.ModuleType("snap7")
    client = types.ModuleType("snap7.client")
    util = types.ModuleType("snap7.util")
    client.Client = object
    snap7.client = client
    util.get_dword = lambda data, offset: int.from_bytes(data[offset:offset + 4], "big")
    util.get_int = lambda data, offset: int.from_bytes(data[offset:offset + 2], "big", signed=True)
    sys.modules["snap7"] = snap7
    sys.modules["snap7.client"] = client
    sys.modules["snap7.util"] = util


def _module():
    _install_snap7()
    return load_module("snap7_collector", siemens_collector_path("snap7_collector.py"), "siemens_collectors_snap7")


class _Client:
    def __init__(self, state="S7CpuStatusRun", connect_exc=None, fail_info=False, fail_memory=False, fail_diag=False):
        self.state = state
        self.connect_exc = connect_exc
        self.fail_info = fail_info
        self.fail_memory = fail_memory
        self.fail_diag = fail_diag
        self.disconnected = False

    def set_connection_type(self, connection_type):
        self.connection_type = connection_type

    def connect(self, host, rack, slot):
        if self.connect_exc:
            raise self.connect_exc

    def disconnect(self):
        self.disconnected = True

    def get_cpu_info(self):
        if self.fail_info:
            raise RuntimeError("info failed")
        return SimpleNamespace(
            ModuleTypeName=b"S7-1500\x00",
            SWVersion=b"V2.9\x00",
            SerialNumber=b"SN123\x00",
        )

    def get_cpu_state(self):
        return self.state

    def read_szl(self, szl_id, index):
        if szl_id == 0x0090:
            if self.fail_memory:
                raise RuntimeError("memory failed")
            entry = bytearray(18)
            entry[2:6] = (50).to_bytes(4, "big")
            entry[6:10] = (100).to_bytes(4, "big")
            entry[10:14] = (25).to_bytes(4, "big")
            entry[14:18] = (100).to_bytes(4, "big")
            return SimpleNamespace(list=[bytes(entry)])
        if self.fail_diag:
            raise RuntimeError("diag failed")
        return SimpleNamespace(list=[(123).to_bytes(2, "big")])


def _collector(module):
    return module.Snap7Collector({
        "id": "plc-1",
        "display_name": "PLC 1",
        "plant": "Plant",
        "config": {"snap7_host": "10.0.0.10"},
    })


def test_snap7_success(monkeypatch):
    module = _module()
    client = _Client()
    monkeypatch.setattr(module.snap7.client, "Client", lambda: client)

    metric = _collector(module).collect()

    assert is_dataclass(metric)
    assert metric.reachable is True
    assert metric.model == "S7-1500"
    assert metric.firmware == "V2.9"
    assert metric.serial_number == "SN123"
    assert metric.cpu_state == "RUN"
    assert metric.load_memory_used_percent == 50.0
    assert metric.work_memory_used_percent == 25.0
    assert metric.last_error_code == 123
    assert client.disconnected is True


def test_snap7_stop_is_reachable(monkeypatch):
    module = _module()
    client = _Client(state="S7CpuStatusStop")
    monkeypatch.setattr(module.snap7.client, "Client", lambda: client)

    metric = _collector(module).collect()

    assert metric.reachable is True
    assert metric.cpu_state == "STOP"
    assert metric.cpu_state_code == 0x04


def test_snap7_partial_failures_keep_successful_values(monkeypatch):
    module = _module()
    client = _Client(fail_info=True, fail_memory=True, fail_diag=True)
    monkeypatch.setattr(module.snap7.client, "Client", lambda: client)

    metric = _collector(module).collect()

    assert metric.reachable is True
    assert metric.cpu_state == "RUN"
    assert metric.model == ""
    assert metric.load_memory_used_percent == 0.0
    assert metric.last_error_code is None


def test_snap7_connection_failure_returns_error_metric(monkeypatch):
    module = _module()
    client = _Client(connect_exc=RuntimeError("connect failed"))
    monkeypatch.setattr(module.snap7.client, "Client", lambda: client)

    metric = _collector(module).collect()
    assert metric.reachable is False
    assert metric.last_error_text == "connect failed"
    assert client.disconnected is True
