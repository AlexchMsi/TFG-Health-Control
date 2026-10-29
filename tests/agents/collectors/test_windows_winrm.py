import json
import sys
import types
from dataclasses import is_dataclass

from tests.agents.collectors.import_helpers import load_module, server_collector_path


class _Result:
    def __init__(self, status_code, stdout=b"", stderr=b""):
        self.status_code = status_code
        self.std_out = stdout
        self.std_err = stderr


def _module(result):
    winrm = types.ModuleType("winrm")

    class Session:
        def __init__(self, *args, **kwargs):
            pass

        def run_ps(self, script):
            return result

    winrm.Session = Session
    sys.modules["winrm"] = winrm
    return load_module("windows_winrm", server_collector_path("windows_winrm.py"), "server_collectors_winrm")


def _collector(module):
    return module.WindowsWinRMCollector({"id": "srv-1", "hostname": "win-host", "critical_services": ["W32Time"]})


def test_winrm_success():
    payload = {
        "Hostname": "WIN01",
        "OSVersion": "Windows Server 2022",
        "UptimeSecs": 3600,
        "CPUPercent": 12.5,
        "RAMTotalGB": 16,
        "RAMFreeGB": 4,
        "Disks": [{"Drive": "C:", "TotalGB": 100, "UsedGB": 25}],
        "NTPOffsetMs": 3.5,
        "NTPServer": "time.local",
        "Services": [{"Name": "W32Time", "DisplayName": "Windows Time", "State": "Running", "StartMode": "Auto"}],
    }
    module = _module(_Result(0, json.dumps(payload).encode()))

    metric = _collector(module).collect()[0]

    assert is_dataclass(metric)
    assert metric.reachable is True
    assert metric.hostname == "WIN01"
    assert metric.ram_used_gb == 12.0
    assert metric.ram_usage_percent == 75.0
    assert metric.disks[0].usage_percent == 25.0
    assert metric.services[0].is_running is True


def test_winrm_status_error_returns_unreachable():
    module = _module(_Result(1, stderr=b"access denied"))

    metric = _collector(module).collect()[0]

    assert metric.reachable is False
    assert metric.collection_method == "winrm"


def test_winrm_json_error_returns_unreachable():
    module = _module(_Result(0, b'{"Error": "powershell failed"}'))

    metric = _collector(module).collect()[0]

    assert metric.reachable is False


def test_winrm_invalid_json_returns_unreachable():
    module = _module(_Result(0, b"not json"))

    metric = _collector(module).collect()[0]

    assert metric.reachable is False
