import sys
import types
from dataclasses import is_dataclass

from tests.agents.collectors.import_helpers import load_module, server_collector_path


def _install_pysnmp():
    pysnmp = types.ModuleType("pysnmp")
    hlapi = types.ModuleType("pysnmp.hlapi")
    hlapi.CommunityData = lambda *args, **kwargs: None
    hlapi.ContextData = lambda *args, **kwargs: None
    hlapi.ObjectIdentity = lambda *args, **kwargs: None
    hlapi.ObjectType = lambda *args, **kwargs: None
    hlapi.SnmpEngine = lambda *args, **kwargs: None
    hlapi.UdpTransportTarget = lambda *args, **kwargs: None
    hlapi.getCmd = lambda *args, **kwargs: iter(())
    hlapi.nextCmd = lambda *args, **kwargs: iter(())
    sys.modules["pysnmp"] = pysnmp
    sys.modules["pysnmp.hlapi"] = hlapi


def _module():
    _install_pysnmp()
    return load_module("windows_snmp", server_collector_path("windows_snmp.py"), "server_collectors_snmp")


def _collector(module):
    return module.WindowsSNMPCollector({"id": "srv-1", "hostname": "10.0.0.1"})


def test_snmp_success(monkeypatch):
    module = _module()
    collector = _collector(module)

    def fake_get(oid):
        return {
            module.OID_SYS_UPTIME: "123400",
            module.OID_SYS_DESCR: "Windows Server 2022",
        }.get(oid)

    def fake_walk(oid):
        rows = {
            module.OID_HR_PROCESSOR_LOAD: [("cpu.1", "10"), ("cpu.2", "30")],
            module.OID_HR_STORAGE_TYPE: [
                (f"{module.OID_HR_STORAGE_TYPE}.1", module.STORAGE_TYPE_RAM),
                (f"{module.OID_HR_STORAGE_TYPE}.2", module.STORAGE_TYPE_DISK),
            ],
            module.OID_HR_STORAGE_DESCR: [
                (f"{module.OID_HR_STORAGE_DESCR}.1", "Physical Memory"),
                (f"{module.OID_HR_STORAGE_DESCR}.2", "C:"),
            ],
            module.OID_HR_STORAGE_ALLOC_UNITS: [
                (f"{module.OID_HR_STORAGE_ALLOC_UNITS}.1", str(1024**2)),
                (f"{module.OID_HR_STORAGE_ALLOC_UNITS}.2", str(1024**2)),
            ],
            module.OID_HR_STORAGE_SIZE: [
                (f"{module.OID_HR_STORAGE_SIZE}.1", "8192"),
                (f"{module.OID_HR_STORAGE_SIZE}.2", "102400"),
            ],
            module.OID_HR_STORAGE_USED: [
                (f"{module.OID_HR_STORAGE_USED}.1", "4096"),
                (f"{module.OID_HR_STORAGE_USED}.2", "51200"),
            ],
        }
        return rows.get(oid, [])

    monkeypatch.setattr(collector, "_get", fake_get)
    monkeypatch.setattr(collector, "_walk", fake_walk)

    metrics = collector.collect()

    assert len(metrics) == 1
    metric = metrics[0]
    assert is_dataclass(metric)
    assert metric.reachable is True
    assert metric.uptime_seconds == 1234
    assert metric.cpu_usage_percent == 20.0
    assert metric.ram_total_gb == 8.0
    assert metric.ram_used_gb == 4.0
    assert metric.disks[0].drive_letter == "C:"


def test_snmp_failure_returns_unreachable(monkeypatch):
    module = _module()
    collector = _collector(module)
    monkeypatch.setattr(collector, "_get", lambda oid: None)

    metric = collector.collect()[0]

    assert is_dataclass(metric)
    assert metric.reachable is False
    assert metric.collection_method == "snmp"


def test_snmp_partial_tables_still_returns_reachable_metric(monkeypatch):
    module = _module()
    collector = _collector(module)
    monkeypatch.setattr(collector, "_get", lambda oid: "not-a-number" if oid == module.OID_SYS_UPTIME else "")
    monkeypatch.setattr(collector, "_walk", lambda oid: [("cpu.1", "bad")] if oid == module.OID_HR_PROCESSOR_LOAD else [])

    metric = collector.collect()[0]

    assert metric.reachable is True
    assert metric.cpu_usage_percent == 0.0
    assert metric.ram_total_gb == 0.0
    assert metric.disks == []
