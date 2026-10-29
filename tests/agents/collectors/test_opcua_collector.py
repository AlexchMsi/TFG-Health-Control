import sys
import types
from dataclasses import is_dataclass

from tests.agents.collectors.import_helpers import load_module, siemens_collector_path


def _install_asyncua():
    asyncua = types.ModuleType("asyncua")
    asyncua.Client = object
    common = types.ModuleType("asyncua.common")
    node = types.ModuleType("asyncua.common.node")
    node.Node = object
    sys.modules["asyncua"] = asyncua
    sys.modules["asyncua.common"] = common
    sys.modules["asyncua.common.node"] = node


def _module():
    _install_asyncua()
    return load_module("opcua_collector", siemens_collector_path("opcua_collector.py"), "siemens_collectors_opcua")


class _Node:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    async def read_value(self):
        if self.exc:
            raise self.exc
        return self.value


class _Client:
    def __init__(self, nodes=None, enter_exc=None):
        self.nodes = nodes or {}
        self.enter_exc = enter_exc

    async def __aenter__(self):
        if self.enter_exc:
            raise self.enter_exc
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get_node(self, node_id):
        node = self.nodes.get(node_id)
        if isinstance(node, Exception):
            raise node
        return node


def _collector(module):
    return module.OpcuaCollector({
        "id": "plc-1",
        "display_name": "PLC 1",
        "plant": "Plant",
        "config": {"opcua_url": "opc.tcp://plc:4840"},
    })


def test_opcua_run(monkeypatch):
    module = _module()
    client = _Client({module._SERVER_STATE_NODE: _Node(0)})
    monkeypatch.setattr(module, "Client", lambda **kwargs: client)

    metric = _collector(module).collect()

    assert is_dataclass(metric)
    assert metric.reachable is True
    assert metric.cpu_state == "RUN"
    assert metric.cpu_state_code == 0


def test_opcua_fault_state_is_still_reachable(monkeypatch):
    module = _module()
    client = _Client({module._SERVER_STATE_NODE: _Node(1)})
    monkeypatch.setattr(module, "Client", lambda **kwargs: client)

    metric = _collector(module).collect()

    assert metric.reachable is True
    assert metric.cpu_state == "FAULT"


def test_opcua_connection_failure_returns_error_metric(monkeypatch):
    module = _module()
    client = _Client(enter_exc=RuntimeError("connect failed"))
    monkeypatch.setattr(module, "Client", lambda **kwargs: client)

    metric = _collector(module).collect()

    assert metric.reachable is False
    assert metric.last_error_text == "connect failed"


def test_opcua_optional_read_failure_is_ignored(monkeypatch):
    module = _module()
    client = _Client({
        module._SERVER_STATE_NODE: _Node(0),
        "ns=3;s=DeviceSet/PLC_1/Resources/CPU/ProgramData": RuntimeError("missing"),
        "ns=3;s=DataBlocksGlobal": RuntimeError("missing"),
    })
    monkeypatch.setattr(module, "Client", lambda **kwargs: client)

    metric = _collector(module).collect()

    assert metric.reachable is True
    assert metric.last_error_text == ""
