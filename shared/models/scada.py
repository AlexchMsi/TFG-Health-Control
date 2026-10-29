from dataclasses import dataclass
from typing import Optional

from .base import BaseMetric


@dataclass
class ScadaTagMetric(BaseMetric):
    scada_type: str = "unknown"
    tag_name: str = ""
    node_id: str = ""
    value_float: Optional[float] = None
    value_string: Optional[str] = None
    value_bool: Optional[bool] = None
    quality: str = "UNKNOWN"
    last_error_text: str = ""
