import sys
import types
from dataclasses import is_dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tests.agents.collectors.import_helpers import load_module, server_collector_path


def _install_vmware():
    pyvim = types.ModuleType("pyVim")
    connect = types.ModuleType("pyVim.connect")
    connect.SmartConnect = lambda **kwargs: None
    connect.Disconnect = lambda si: None
    pyvmomi = types.ModuleType("pyVmomi")
    vim = types.SimpleNamespace(HostSystem=type("HostSystem", (), {}), VirtualMachine=type("VirtualMachine", (), {}))
    pyvmomi.vim = vim
    sys.modules["pyVim"] = pyvim
    sys.modules["pyVim.connect"] = connect
    sys.modules["pyVmomi"] = pyvmomi


def _module():
    _install_vmware()
    return load_module("vmware", server_collector_path("vmware.py"), "server_collectors_vmware")


class _View:
    def __init__(self, items):
        self.view = items
        self.destroyed = False

    def Destroy(self):
        self.destroyed = True


def _content(module, hosts, vms):
    class ViewManager:
        def CreateContainerView(self, root, types_, recursive):
            if types_[0] is module.vim.HostSystem:
                return _View(hosts)
            return _View(vms)

    return SimpleNamespace(rootFolder=object(), viewManager=ViewManager())


def _collector(module):
    return module.VMwareCollector({"host": "vc.local", "user": "u", "password": "p", "ignore_ssl": True})


def _host():
    boot = datetime.now(timezone.utc) - timedelta(hours=1)
    summary = SimpleNamespace(
        host=SimpleNamespace(_moId="host-1"),
        hardware=SimpleNamespace(cpuMhz=2400, numCpuCores=4, memorySize=16 * 1024**3),
        quickStats=SimpleNamespace(overallCpuUsage=2400, overallMemoryUsage=8192),
        runtime=SimpleNamespace(bootTime=boot, connectionState="connected", inMaintenanceMode=False),
        config=SimpleNamespace(name="esxi01", product=SimpleNamespace(version="8.0", build="123")),
    )
    return SimpleNamespace(name="esxi01", summary=summary, vm=[object(), object()])


def _vm():
    boot = datetime.now(timezone.utc) - timedelta(minutes=30)
    host = SimpleNamespace(summary=SimpleNamespace(config=SimpleNamespace(name="esxi01")), _moId="host-1")
    summary = SimpleNamespace(
        vm=SimpleNamespace(_moId="vm-1"),
        quickStats=SimpleNamespace(overallCpuUsage=100, guestMemoryUsage=512, balloonedMemory=0),
        runtime=SimpleNamespace(bootTime=boot, powerState="poweredOn", host=host),
        config=SimpleNamespace(name="app01", guestFullName="Ubuntu"),
        guest=SimpleNamespace(toolsStatus="toolsOk"),
    )
    return SimpleNamespace(name="app01", summary=summary, snapshot=None)


def test_vmware_collects_host_and_vm(monkeypatch):
    module = _module()
    collector = _collector(module)
    content = _content(module, [_host()], [_vm()])
    collector._si = SimpleNamespace(RetrieveContent=lambda: content)
    monkeypatch.setattr(collector, "_connect", lambda: None)
    monkeypatch.setattr(module, "Disconnect", lambda si: None)

    metrics = collector.collect()

    assert len(metrics) == 2
    assert all(is_dataclass(metric) for metric in metrics)
    assert metrics[0].hostname == "esxi01"
    assert metrics[0].cpu_usage_percent == 25.0
    assert metrics[1].vm_name == "app01"
    assert metrics[1].power_state == "poweredOn"


def test_vmware_bad_entities_are_skipped(monkeypatch):
    module = _module()
    collector = _collector(module)
    content = _content(module, [SimpleNamespace(name="bad-host")], [SimpleNamespace(name="bad-vm")])
    collector._si = SimpleNamespace(RetrieveContent=lambda: content)
    monkeypatch.setattr(collector, "_connect", lambda: None)
    monkeypatch.setattr(module, "Disconnect", lambda si: None)

    assert collector.collect() == []


def test_vmware_connection_failure_returns_unreachable_host_metric(monkeypatch):
    module = _module()
    collector = _collector(module)
    monkeypatch.setattr(collector, "_connect", lambda: (_ for _ in ()).throw(RuntimeError("no vcenter")))

    metrics = collector.collect()

    assert len(metrics) == 1
    assert metrics[0].reachable is False
    assert metrics[0].source_id == "esxi-vc.local"
    assert metrics[0].hostname == "vc.local"
    assert "no vcenter" in metrics[0].last_error_text
