"""
AgentScheduler for the Siemens agent.

Supports dynamic add/remove of targets without restart — used by ConfigPoller.
"""

import json
import logging
from datetime import timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.influx.writer import InfluxWriter
from shared.models.siemens import SiemensPlcMetric

logger = logging.getLogger(__name__)


class AgentScheduler:
    def __init__(self, writer: InfluxWriter) -> None:
        self._writer = writer
        self._aps = BackgroundScheduler(timezone="UTC")

    # ── Public API used by ConfigPoller ───────────────────────────────────────

    def add_target(self, target: dict) -> None:
        target_id = target["id"]
        cfg = target["config"]
        interval = cfg.get("poll_interval_seconds", 30)
        method = cfg.get("collection_method", "auto")

        self._aps.add_job(
            func=self._collect_and_write,
            trigger=IntervalTrigger(seconds=interval, jitter=5),
            id=target_id,
            args=[target, method],
            max_instances=1,
            misfire_grace_time=interval,
            replace_existing=True,
        )
        logger.info("Scheduled target %s (method=%s, interval=%ds)", target_id, method, interval)

    def remove_target(self, target_id: str) -> None:
        if self._aps.get_job(target_id):
            self._aps.remove_job(target_id)
            logger.info("Removed target %s", target_id)

    # ── Scheduler lifecycle ───────────────────────────────────────────────────

    @property
    def aps(self) -> BackgroundScheduler:
        return self._aps

    def start(self) -> None:
        self._aps.start()

    def shutdown(self) -> None:
        self._aps.shutdown(wait=False)

    # ── Collection logic ──────────────────────────────────────────────────────

    def _collect_and_write(self, target: dict, method: str) -> None:
        metric = self._collect(target, method)
        self._write(metric)

    def _collect(self, target: dict, method: str) -> SiemensPlcMetric:
        # Imports deferred per method: a broken/missing protocol library must
        # not take down collection for targets that use the other protocol.
        from .collectors.opcua_collector import OpcuaCollector

        cfg = target["config"]

        if method == "opcua":
            return OpcuaCollector(target).collect()

        if method == "snap7":
            from .collectors.snap7_collector import Snap7Collector
            return Snap7Collector(target).collect()

        # method == "auto": try OPC UA first, fall back to Snap7 only when the
        # OPC UA *connection* failed (reachable=False). A reachable PLC in STOP
        # is a valid result and must not trigger the fallback.
        if cfg.get("opcua_url"):
            m = OpcuaCollector(target).collect()
            if m.reachable:
                return m
            logger.debug("OPC UA connection failed for %s — trying Snap7 fallback", target["id"])

        if cfg.get("snap7_host"):
            from .collectors.snap7_collector import Snap7Collector
            return Snap7Collector(target).collect()

        # Neither configured
        return SiemensPlcMetric(
            source_id=target["id"],
            source_type="siemens_plc",
            plc_name=target["display_name"],
            plant=target["plant"],
            collection_method="auto",
            reachable=False,
            last_error_text="No valid collection method configured",
        )

    def _write(self, metric: SiemensPlcMetric) -> None:
        # Empty tag values are dropped by the InfluxDB client, which would make
        # the API's pivot (rowKey includes model/firmware) return no rows.
        # Write a stable placeholder instead.
        tags = {
            "source_id": metric.source_id,
            "plc_name": metric.plc_name,
            "plant": metric.plant,
            "model": metric.model or "unknown",
            "firmware": metric.firmware or "unknown",
            "collection_method": metric.collection_method,
        }
        fields = {
            "reachable": int(metric.reachable),
            "cpu_state": metric.cpu_state,
            "cpu_state_code": metric.cpu_state_code,
            "load_memory_used_percent": metric.load_memory_used_percent,
            "work_memory_used_percent": metric.work_memory_used_percent,
            "cycle_time_ms": metric.cycle_time_ms,
            "uptime_seconds": metric.uptime_seconds,
        }
        if metric.battery_ok is not None:
            fields["battery_ok"] = int(metric.battery_ok)
        if metric.last_error_code is not None:
            fields["last_error_code"] = metric.last_error_code
        if metric.last_error_text:
            fields["last_error_text"] = metric.last_error_text

        try:
            self._writer.write_point(
                measurement="siemens_plc_health",
                tags=tags,
                fields=fields,
                timestamp=metric.collected_at,
            )
        except Exception as exc:
            logger.error("InfluxDB write error for %s: %s", metric.source_id, exc)
