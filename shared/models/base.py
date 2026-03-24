from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class BaseMetric:
    """Base class for all collected metrics."""
    source_id: str          # Unique identifier (hostname, IP, PLC tag, VM name)
    source_type: str        # "windows_server", "esxi_host", "vm", "siemens_plc", etc.
    collected_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reachable: bool = True  # False when collection failed — written to InfluxDB
                            # so Grafana can alert on connectivity gaps
