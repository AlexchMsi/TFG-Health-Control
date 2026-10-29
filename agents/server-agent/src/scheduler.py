"""
Agent scheduling — one APScheduler job per configured target.
Supports dynamic add/remove of targets via ConfigPoller (no restart needed).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from shared.influx.writer import InfluxWriter, WriteError
from shared.models.base import BaseMetric
from shared.models.server import WindowsServerMetric, DiskMetric, ServiceStatus
from shared.models.vmware import ESXiHostMetric, VMMetric

from .collectors.base import AbstractCollector
from .collectors.windows_snmp import WindowsSNMPCollector
from .collectors.windows_winrm import WindowsWinRMCollector
from .collectors.vmware import VMwareCollector

logger = logging.getLogger(__name__)


class AgentScheduler:
    def __init__(self, writer: InfluxWriter) -> None:
        self._aps = BackgroundScheduler(timezone="UTC")
        self._writer = writer

    # ── Public API used by ConfigPoller ──────────────────────────────────────

    def add_target(self, target: dict) -> None:
        cfg = target["config"]
        flat_cfg = {"id": target["id"], **cfg}
        collector = self._build_windows_collector(flat_cfg)
        interval = cfg.get("poll_interval_seconds", 60)
        self._aps.add_job(
            func=self._run_collection,
            trigger=IntervalTrigger(seconds=interval, jitter=5),
            args=[collector],
            id=f"windows_{target['id']}",
            max_instances=1,
            misfire_grace_time=interval,
            replace_existing=True,
        )
        logger.info("add_target id=%s method=%s interval=%ds",
                    target["id"], cfg.get("collection_method", "snmp"), interval)

    def remove_target(self, target_id: str) -> None:
        job_id = f"windows_{target_id}"
        if self._aps.get_job(job_id):
            self._aps.remove_job(job_id)
            logger.info("remove_target id=%s", target_id)

    @property
    def aps(self) -> BackgroundScheduler:
        return self._aps

    def _build_windows_collector(self, cfg: dict) -> AbstractCollector:
        method = cfg.get("collection_method", "snmp")
        if method == "winrm":
            return WindowsWinRMCollector(cfg)
        if method == "vmware":
            return VMwareCollector(cfg)
        return WindowsSNMPCollector(cfg)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        self._aps.start()
        logger.info("agent_scheduler_started")

    def shutdown(self) -> None:
        self._aps.shutdown(wait=False)

    # ── Job execution ────────────────────────────────────────────────────────

    def _run_collection(self, collector: AbstractCollector) -> None:
        metrics = collector.collect()
        for metric in metrics:
            try:
                self._write_metric(metric)
            except WriteError as exc:
                logger.error("write_error metric=%s error=%s",
                             metric.source_id, exc)

    def _write_metric(self, metric: BaseMetric) -> None:
        ts = metric.collected_at

        if isinstance(metric, WindowsServerMetric):
            self._write_windows(metric, ts)
        elif isinstance(metric, ESXiHostMetric):
            self._write_esxi(metric, ts)
        elif isinstance(metric, VMMetric):
            self._write_vm(metric, ts)

    def _write_windows(self, m: WindowsServerMetric, ts: datetime) -> None:
        # Main server health point
        self._writer.write_point(
            measurement="server_health",
            tags={
                "source_id": m.source_id,
                "source_type": m.source_type,
                "hostname": m.hostname,
                "collection_method": m.collection_method,
            },
            fields={
                "cpu_usage_percent": m.cpu_usage_percent,
                "cpu_core_count": m.cpu_core_count,
                "ram_total_gb": m.ram_total_gb,
                "ram_used_gb": m.ram_used_gb,
                "ram_usage_percent": m.ram_usage_percent,
                "uptime_seconds": m.uptime_seconds,
                "clock_offset_ms": m.clock_offset_ms,
                "reachable": int(m.reachable),
            },
            timestamp=ts,
        )
        # One point per disk
        for disk in m.disks:
            self._write_disk(m.source_id, disk, ts)
        # One point per service
        for svc in m.services:
            self._write_service(m.source_id, svc, ts)

    def _write_disk(self, source_id: str, d: DiskMetric, ts: datetime) -> None:
        self._writer.write_point(
            measurement="disk_health",
            tags={"source_id": source_id, "drive_letter": d.drive_letter},
            fields={
                "total_gb": d.total_gb,
                "used_gb": d.used_gb,
                "usage_percent": d.usage_percent,
            },
            timestamp=ts,
        )

    def _write_service(self, source_id: str, s: ServiceStatus, ts: datetime) -> None:
        self._writer.write_point(
            measurement="service_health",
            tags={"source_id": source_id, "service_name": s.name},
            fields={
                "state": s.state,
                "is_running": int(s.is_running),
                "start_mode": s.start_mode,
            },
            timestamp=ts,
        )

    def _write_esxi(self, m: ESXiHostMetric, ts: datetime) -> None:
        fields = {
            "cpu_usage_percent": m.cpu_usage_percent,
            "cpu_used_mhz": m.cpu_used_mhz,
            "cpu_total_mhz": m.cpu_total_mhz,
            "ram_total_gb": m.ram_total_gb,
            "ram_used_gb": m.ram_used_gb,
            "ram_usage_percent": m.ram_usage_percent,
            "uptime_seconds": m.uptime_seconds,
            "connection_state": m.connection_state,
            "maintenance_mode": int(m.maintenance_mode),
            "num_vms": m.num_vms,
            "reachable": int(m.reachable),
        }
        if m.last_error_text:
            fields["last_error_text"] = m.last_error_text
        self._writer.write_point(
            measurement="esxi_health",
            tags={
                "source_id": m.source_id,
                "source_type": m.source_type,
                "hostname": m.hostname,
                # Empty tags are dropped by the client and break the API pivot.
                "version": m.version or "unknown",
            },
            fields=fields,
            timestamp=ts,
        )

    def _write_vm(self, m: VMMetric, ts: datetime) -> None:
        self._writer.write_point(
            measurement="vm_health",
            tags={
                "source_id": m.source_id,
                "source_type": m.source_type,
                "vm_name": m.vm_name,
                "esxi_host": m.esxi_host,
                # Empty tags are dropped by the client and break the API pivot.
                "guest_os": m.guest_os or "unknown",
            },
            fields={
                "power_state": m.power_state,
                "is_powered_on": int(m.is_powered_on),
                "cpu_usage_mhz": m.cpu_usage_mhz,
                "ram_usage_mb": m.ram_usage_mb,
                "ram_balloon_mb": m.ram_balloon_mb,
                "uptime_seconds": m.uptime_seconds,
                "tools_status": m.tools_status,
                "num_snapshots": m.num_snapshots,
                "oldest_snapshot_age_days": m.oldest_snapshot_age_days,
                "reachable": int(m.reachable),
            },
            timestamp=ts,
        )

