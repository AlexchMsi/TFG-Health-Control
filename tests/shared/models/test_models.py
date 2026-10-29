from dataclasses import is_dataclass
from datetime import timezone

from shared.models.base import BaseMetric
from shared.models.server import DiskMetric, ServiceStatus, WindowsServerMetric
from shared.models.siemens import SiemensDiagnosticEvent, SiemensPlcMetric
from shared.models.vmware import ESXiHostMetric, VMMetric


def test_base_metric_defaults_to_reachable_with_utc_timestamp():
    metric = BaseMetric(source_id="source-1", source_type="server")

    assert is_dataclass(metric)
    assert metric.reachable is True
    assert metric.collected_at.tzinfo == timezone.utc


def test_metric_subclasses_are_dataclasses_and_keep_base_fields():
    metrics = [
        WindowsServerMetric(source_id="srv-1", source_type="windows_server", reachable=False),
        SiemensPlcMetric(source_id="plc-1", source_type="siemens_plc"),
        ESXiHostMetric(source_id="esxi-1", source_type="esxi_host"),
        VMMetric(source_id="vm-1", source_type="vm"),
    ]

    assert all(is_dataclass(metric) for metric in metrics)
    assert metrics[0].reachable is False
    assert [metric.source_id for metric in metrics] == ["srv-1", "plc-1", "esxi-1", "vm-1"]


def test_windows_server_nested_defaults_are_independent_lists():
    first = WindowsServerMetric(source_id="srv-1", source_type="windows_server")
    second = WindowsServerMetric(source_id="srv-2", source_type="windows_server")

    first.disks.append(DiskMetric("C:", 100.0, 50.0, 50.0))
    first.services.append(ServiceStatus("W32Time", "Windows Time", "Running", "Auto"))

    assert second.disks == []
    assert second.services == []


def test_service_status_is_running_is_case_insensitive():
    assert ServiceStatus("svc", "Service", "Running", "Auto").is_running is True
    assert ServiceStatus("svc", "Service", "running", "Auto").is_running is True
    assert ServiceStatus("svc", "Service", "Stopped", "Auto").is_running is False


def test_vm_power_state_helper_matches_powered_on_literal():
    assert VMMetric(source_id="vm-1", source_type="vm", power_state="poweredOn").is_powered_on is True
    assert VMMetric(source_id="vm-1", source_type="vm", power_state="poweredOff").is_powered_on is False


def test_siemens_diagnostic_event_is_dataclass():
    event = SiemensDiagnosticEvent(
        source_id="plc-1",
        plc_name="PLC 1",
        plant="Plant",
        event_id=1,
        event_text="Started",
    )

    assert is_dataclass(event)
    assert event.severity == "info"
