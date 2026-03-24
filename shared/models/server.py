from dataclasses import dataclass, field
from .base import BaseMetric


@dataclass
class DiskMetric:
    drive_letter: str       # e.g. "C:", "D:", "/dev/sda1"
    total_gb: float
    used_gb: float
    usage_percent: float


@dataclass
class ServiceStatus:
    name: str               # e.g. "W32Time", "WinRM", "SCADA Runtime"
    display_name: str
    state: str              # "Running", "Stopped", "Paused"
    start_mode: str         # "Auto", "Manual", "Disabled"

    @property
    def is_running(self) -> bool:
        return self.state.lower() == "running"


@dataclass
class WindowsServerMetric(BaseMetric):
    # Identification
    hostname: str = ""
    os_version: str = ""
    collection_method: str = "snmp"  # "snmp" | "winrm"

    # CPU
    cpu_usage_percent: float = 0.0
    cpu_core_count: int = 0

    # RAM
    ram_total_gb: float = 0.0
    ram_used_gb: float = 0.0
    ram_usage_percent: float = 0.0

    # Clock sync (available via WinRM only)
    clock_offset_ms: float | None = None
    ntp_server: str | None = None

    # System uptime in seconds
    uptime_seconds: int = 0

    # Disk volumes (one DiskMetric per volume)
    disks: list[DiskMetric] = field(default_factory=list)

    # Critical services (available via WinRM only)
    services: list[ServiceStatus] = field(default_factory=list)
