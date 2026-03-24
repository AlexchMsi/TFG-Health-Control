"""
VMware vSphere Collector.

Uses pyVmomi to connect to a vCenter Server or standalone ESXi host
and collect health metrics for:
  - ESXi hosts (CPU, RAM, state, maintenance mode, uptime)
  - Virtual machines (power state, CPU/RAM usage, snapshots, VMware Tools)

SSL: supports self-signed certificates (common in OT environments) via ignore_ssl=True.
"""
from __future__ import annotations

import logging
import ssl
from datetime import datetime, timezone

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from .base import AbstractCollector
from shared.models.base import BaseMetric
from shared.models.vmware import ESXiHostMetric, VMMetric

logger = logging.getLogger(__name__)


class VMwareCollector(AbstractCollector):
    """Collect VMware ESXi host and VM metrics via vSphere API."""

    def __init__(self, config: dict) -> None:
        self.host: str = config["host"]
        self.user: str = config["user"]
        self.password: str = config["password"]
        self.ignore_ssl: bool = config.get("ignore_ssl", False)
        self.collect_hosts: bool = config.get("collect_hosts", True)
        self.collect_vms: bool = config.get("collect_vms", True)
        self._si = None  # vSphere ServiceInstance

    def collect(self) -> list[BaseMetric]:
        """Returns a mix of ESXiHostMetric and VMMetric objects."""
        try:
            self._connect()
            content = self._si.RetrieveContent()
            metrics: list[BaseMetric] = []
            if self.collect_hosts:
                metrics.extend(self._collect_hosts(content))
            if self.collect_vms:
                metrics.extend(self._collect_vms(content))
            logger.info("vmware_collected hosts=%d vms=%d",
                        sum(1 for m in metrics if isinstance(m, ESXiHostMetric)),
                        sum(1 for m in metrics if isinstance(m, VMMetric)))
            return metrics
        except Exception as exc:
            logger.error("vmware_collection_failed host=%s error=%s", self.host, exc)
            return []
        finally:
            if self._si:
                Disconnect(self._si)
                self._si = None

    # ── Connection ───────────────────────────────────────────────────────────

    def _connect(self) -> None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if self.ignore_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        self._si = SmartConnect(
            host=self.host,
            user=self.user,
            pwd=self.password,
            sslContext=context,
        )

    # ── ESXi Hosts ───────────────────────────────────────────────────────────

    def _collect_hosts(self, content) -> list[ESXiHostMetric]:
        view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True
        )
        results = []
        for host in view.view:
            try:
                results.append(self._parse_host(host))
            except Exception as exc:
                logger.warning("vmware_host_parse_error host=%s error=%s",
                               getattr(host, "name", "?"), exc)
        view.Destroy()
        return results

    def _parse_host(self, host: vim.HostSystem) -> ESXiHostMetric:
        summary = host.summary
        hw = summary.hardware
        qs = summary.quickStats
        runtime = summary.runtime
        config = summary.config

        cpu_total_mhz = hw.cpuMhz * hw.numCpuCores if hw else 0
        cpu_used_mhz = qs.overallCpuUsage or 0
        cpu_pct = round(cpu_used_mhz / cpu_total_mhz * 100, 2) if cpu_total_mhz > 0 else 0.0

        ram_total_gb = round((hw.memorySize or 0) / (1024 ** 3), 2)
        ram_used_gb = round((qs.overallMemoryUsage or 0) / 1024, 2)  # MB → GB
        ram_pct = round(ram_used_gb / ram_total_gb * 100, 2) if ram_total_gb > 0 else 0.0

        # Count VMs on this host
        num_vms = len(host.vm) if host.vm else 0

        return ESXiHostMetric(
            source_id=f"esxi-{summary.host._moId}",
            source_type="esxi_host",
            hostname=config.name if config else host.name,
            version=config.product.version if (config and config.product) else "",
            build=config.product.build if (config and config.product) else "",
            cpu_usage_percent=cpu_pct,
            cpu_num_cores=hw.numCpuCores if hw else 0,
            cpu_total_mhz=cpu_total_mhz,
            cpu_used_mhz=cpu_used_mhz,
            ram_total_gb=ram_total_gb,
            ram_used_gb=ram_used_gb,
            ram_usage_percent=ram_pct,
            uptime_seconds=runtime.bootTime and self._uptime_from_boot(runtime.bootTime) or 0,
            connection_state=str(runtime.connectionState),
            maintenance_mode=bool(runtime.inMaintenanceMode),
            num_vms=num_vms,
            reachable=True,
        )

    # ── Virtual Machines ─────────────────────────────────────────────────────

    def _collect_vms(self, content) -> list[VMMetric]:
        view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        results = []
        for vm in view.view:
            try:
                results.append(self._parse_vm(vm))
            except Exception as exc:
                logger.warning("vmware_vm_parse_error vm=%s error=%s",
                               getattr(vm, "name", "?"), exc)
        view.Destroy()
        return results

    def _parse_vm(self, vm: vim.VirtualMachine) -> VMMetric:
        summary = vm.summary
        qs = summary.quickStats
        runtime = summary.runtime
        config = summary.config
        guest = summary.guest

        # Determine which ESXi host this VM runs on
        esxi_host = ""
        if runtime.host:
            try:
                esxi_host = runtime.host.summary.config.name
            except Exception:
                esxi_host = str(runtime.host._moId)

        num_snaps, oldest_snap_days = self._get_snapshot_info(vm)

        return VMMetric(
            source_id=f"vm-{summary.vm._moId}",
            source_type="virtual_machine",
            vm_name=config.name if config else vm.name,
            esxi_host=esxi_host,
            guest_os=config.guestFullName if config else "",
            power_state=str(runtime.powerState),
            cpu_usage_mhz=qs.overallCpuUsage or 0,
            ram_usage_mb=qs.guestMemoryUsage or 0,
            ram_balloon_mb=qs.balloonedMemory or 0,
            uptime_seconds=runtime.bootTime and self._uptime_from_boot(runtime.bootTime) or 0,
            tools_status=str(guest.toolsStatus) if guest else "toolsNotInstalled",
            num_snapshots=num_snaps,
            oldest_snapshot_age_days=oldest_snap_days,
            reachable=True,
        )

    # ── Snapshot helpers ─────────────────────────────────────────────────────

    def _get_snapshot_info(self, vm: vim.VirtualMachine) -> tuple[int, float | None]:
        """Return (snapshot_count, oldest_snapshot_age_days)."""
        if not vm.snapshot:
            return 0, None
        snapshots: list = []
        self._flatten_snapshots(vm.snapshot.rootSnapshotList, snapshots)
        if not snapshots:
            return 0, None
        oldest_time = min(s.createTime for s in snapshots)
        # oldest_time may be offset-aware or naive depending on pyVmomi version
        now = datetime.now(timezone.utc)
        if oldest_time.tzinfo is None:
            oldest_time = oldest_time.replace(tzinfo=timezone.utc)
        age_days = round((now - oldest_time).total_seconds() / 86400, 1)
        return len(snapshots), age_days

    def _flatten_snapshots(self, snapshot_list, result: list) -> None:
        """Recursive DFS through the snapshot tree."""
        for snap in snapshot_list:
            result.append(snap)
            if snap.childSnapshotList:
                self._flatten_snapshots(snap.childSnapshotList, result)

    # ── Utility ──────────────────────────────────────────────────────────────

    @staticmethod
    def _uptime_from_boot(boot_time: datetime) -> int:
        now = datetime.now(timezone.utc)
        if boot_time.tzinfo is None:
            boot_time = boot_time.replace(tzinfo=timezone.utc)
        return max(0, int((now - boot_time).total_seconds()))
