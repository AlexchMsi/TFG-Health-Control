from dataclasses import dataclass
from .base import BaseMetric


@dataclass
class ESXiHostMetric(BaseMetric):
    hostname: str = ""
    version: str = ""
    build: str = ""

    # CPU
    cpu_usage_percent: float = 0.0
    cpu_num_cores: int = 0
    cpu_total_mhz: int = 0
    cpu_used_mhz: int = 0

    # RAM
    ram_total_gb: float = 0.0
    ram_used_gb: float = 0.0
    ram_usage_percent: float = 0.0

    # State
    uptime_seconds: int = 0
    connection_state: str = ""      # "connected", "disconnected", "notResponding"
    maintenance_mode: bool = False
    num_vms: int = 0


@dataclass
class VMMetric(BaseMetric):
    vm_name: str = ""
    esxi_host: str = ""             # Which host it runs on (tag in InfluxDB)
    guest_os: str = ""

    # Power
    power_state: str = ""           # "poweredOn", "poweredOff", "suspended"

    # CPU
    cpu_usage_mhz: int = 0

    # RAM
    ram_usage_mb: int = 0
    ram_balloon_mb: int = 0

    # I/O (delta since last collection — KB/s)
    disk_read_kbps: float = 0.0
    disk_write_kbps: float = 0.0
    net_rx_kbps: float = 0.0
    net_tx_kbps: float = 0.0

    # State
    uptime_seconds: int = 0
    tools_status: str = ""          # "toolsOk", "toolsOld", "toolsNotInstalled", "toolsNotRunning"

    # Snapshots
    num_snapshots: int = 0
    oldest_snapshot_age_days: float | None = None  # None if no snapshots

    @property
    def is_powered_on(self) -> bool:
        return self.power_state == "poweredOn"
