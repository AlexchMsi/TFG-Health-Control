from typing import Protocol

from shared.models.base import BaseMetric


class AbstractCollector(Protocol):
    def collect(self) -> list[BaseMetric]: ...
