from abc import ABC, abstractmethod
from shared.models.base import BaseMetric


class AbstractCollector(ABC):
    """
    Base class for all data collectors.

    IMPORTANT: collect() must NEVER raise an exception.
    All errors must be caught internally, logged, and a metric with
    reachable=False must be returned so connectivity gaps are visible in Grafana.
    """

    @abstractmethod
    def collect(self) -> list[BaseMetric]:
        """
        Poll the target and return a list of metric objects.
        On failure: return a list containing a single metric with reachable=False.
        """
        ...

    def validate_connectivity(self) -> bool:
        """
        Quick pre-check before full collection.
        Subclasses may override for a lightweight ping/handshake.
        Default: always returns True (connectivity checked inside collect()).
        """
        return True
