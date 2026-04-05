from dataclasses import dataclass, field
from typing import Optional

from .base import BaseMetric


@dataclass
class SiemensPlcMetric(BaseMetric):
    plc_name: str = ""
    plant: str = ""
    model: str = ""              # "S7-1500", "S7-1200", "S7-300"
    firmware: str = ""
    serial_number: str = ""
    collection_method: str = "opcua"   # "opcua" | "snap7"

    # CPU state
    cpu_state: str = ""          # "RUN", "STOP", "STARTUP", "HOLD", "FAULT"
    cpu_state_code: int = 0      # 8=RUN, 4=STOP, 0=Unknown

    # Memory
    load_memory_used_percent: float = 0.0
    work_memory_used_percent: float = 0.0

    # Diagnostics
    cycle_time_ms: float = 0.0
    uptime_seconds: int = 0
    battery_ok: Optional[bool] = None

    last_error_code: Optional[int] = None
    last_error_text: str = ""


@dataclass
class SiemensDiagnosticEvent:
    """A single entry from the PLC diagnostic buffer."""
    source_id: str
    plc_name: str
    plant: str
    event_id: int
    event_text: str
    severity: str = "info"   # "info" | "warning" | "error"
