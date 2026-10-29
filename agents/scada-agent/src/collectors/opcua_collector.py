import asyncio
import logging
from datetime import datetime, timezone

from asyncua import Client

from shared.models.scada import ScadaTagMetric

from .detector import detect_scada_type

logger = logging.getLogger(__name__)


def _split_value(value):
    if isinstance(value, bool):
        return None, None, value
    if isinstance(value, (int, float)):
        return float(value), None, None
    if value is None:
        return None, None, None
    return None, str(value), None


class OpcuaScadaCollector:
    def __init__(self, config: dict) -> None:
        self.source_id = config["id"]
        self.url = config["opcua_url"]
        self.username = config.get("username")
        self.password = config.get("password")
        self.scada_type = config.get("scada_type", "auto")
        self.tags = config.get("tags", [])
        self.timeout = config.get("timeout_seconds", 10)

    def collect(self) -> list[ScadaTagMetric]:
        try:
            return asyncio.run(self._collect_async())
        except Exception as exc:
            logger.error("collection_failed host=%s error=%s", self.source_id, exc)
            scada_type = self.scada_type if self.scada_type.lower() != "auto" else "unknown"
            return [self._metric(tag, scada_type, False, "BAD", str(exc)) for tag in self.tags]

    async def _collect_async(self) -> list[ScadaTagMetric]:
        scada_type = self.scada_type
        if scada_type.lower() == "auto":
            scada_type = await detect_scada_type(self.url, self.username, self.password, self.timeout)

        metrics = []
        client = Client(url=self.url, timeout=self.timeout)
        if self.username and self.password:
            client.set_user(self.username)
            client.set_password(self.password)
        async with client:
            collected_at = datetime.now(timezone.utc)
            for tag in self.tags:
                try:
                    value = await client.get_node(tag["node_id"]).read_value()
                    value_float, value_string, value_bool = _split_value(value)
                    metrics.append(self._metric(tag, scada_type, True, "GOOD", collected_at=collected_at,
                                                value_float=value_float, value_string=value_string,
                                                value_bool=value_bool))
                except Exception as exc:
                    metrics.append(self._metric(tag, scada_type, False, "BAD", str(exc), collected_at))
        return metrics

    def _metric(self, tag: dict, scada_type: str, reachable: bool, quality: str, last_error_text: str = "",
                collected_at=None, value_float=None, value_string=None, value_bool=None) -> ScadaTagMetric:
        return ScadaTagMetric(
            source_id=self.source_id,
            source_type="scada",
            collected_at=collected_at or datetime.now(timezone.utc),
            reachable=reachable,
            scada_type=scada_type,
            tag_name=tag["name"],
            node_id=tag["node_id"],
            value_float=value_float,
            value_string=value_string,
            value_bool=value_bool,
            quality=quality,
            last_error_text=last_error_text,
        )
