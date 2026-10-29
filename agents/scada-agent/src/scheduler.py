import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.influx.writer import InfluxWriter
from shared.models.scada import ScadaTagMetric

from .collectors.opcua_collector import OpcuaScadaCollector

logger = logging.getLogger(__name__)


class AgentScheduler:
    def __init__(self, writer: InfluxWriter) -> None:
        self._writer = writer
        self._aps = BackgroundScheduler(timezone="UTC")

    def add_target(self, target: dict) -> None:
        cfg = target["config"]
        interval = cfg.get("poll_interval_seconds", 30)
        collector = OpcuaScadaCollector({"id": target["id"], **cfg})
        self._aps.add_job(
            func=self._collect_and_write,
            trigger=IntervalTrigger(seconds=interval, jitter=5),
            args=[collector],
            id=f"scada_{target['id']}",
            max_instances=1,
            misfire_grace_time=interval,
            replace_existing=True,
        )
        logger.info("add_target id=%s type=scada interval=%ds", target["id"], interval)

    def remove_target(self, target_id: str) -> None:
        job_id = f"scada_{target_id}"
        if self._aps.get_job(job_id):
            self._aps.remove_job(job_id)
            logger.info("remove_target id=%s", target_id)

    @property
    def aps(self) -> BackgroundScheduler:
        return self._aps

    def start(self) -> None:
        self._aps.start()

    def shutdown(self) -> None:
        self._aps.shutdown(wait=False)

    def _collect_and_write(self, collector: OpcuaScadaCollector) -> None:
        for metric in collector.collect():
            self._write(metric)

    def _write(self, m: ScadaTagMetric) -> None:
        fields = {
            "value_float": m.value_float,
            "value_string": m.value_string,
            "value_bool": m.value_bool,
            "quality": m.quality,
            "reachable": int(m.reachable),
        }
        if m.last_error_text:
            fields["last_error_text"] = m.last_error_text
        try:
            self._writer.write_point(
                measurement="scada_tag_health",
                tags={"source_id": m.source_id, "scada_type": m.scada_type, "tag_name": m.tag_name},
                fields=fields,
                timestamp=m.collected_at,
            )
        except Exception as exc:
            logger.error("InfluxDB write error for %s/%s: %s", m.source_id, m.tag_name, exc)
