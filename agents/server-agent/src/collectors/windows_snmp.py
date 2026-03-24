"""
Windows SNMP Collector — primary collection path.

Uses HOST-RESOURCES-MIB and IF-MIB to collect CPU, RAM, disk, and uptime
from Windows servers. Requires SNMP service enabled on the target with a
configured community string and permitted source IPs.

No agent installation required on the target.
"""
from __future__ import annotations

import logging
from typing import Any

from pysnmp.hlapi import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    getCmd,
    nextCmd,
)

from .base import AbstractCollector
from shared.models.server import DiskMetric, WindowsServerMetric

logger = logging.getLogger(__name__)

# ── OID constants ────────────────────────────────────────────────────────────
# SNMPv2-MIB
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"

# HOST-RESOURCES-MIB
OID_HR_PROCESSOR_LOAD = "1.3.6.1.2.1.25.3.3.1.2"   # table: one entry per CPU
OID_HR_STORAGE_TYPE = "1.3.6.1.2.1.25.2.3.1.2"
OID_HR_STORAGE_DESCR = "1.3.6.1.2.1.25.2.3.1.3"
OID_HR_STORAGE_ALLOC_UNITS = "1.3.6.1.2.1.25.2.3.1.4"
OID_HR_STORAGE_SIZE = "1.3.6.1.2.1.25.2.3.1.5"
OID_HR_STORAGE_USED = "1.3.6.1.2.1.25.2.3.1.6"

# hrStorageType values
STORAGE_TYPE_RAM = "1.3.6.1.2.1.25.2.1.2"       # hrStorageRam
STORAGE_TYPE_DISK = "1.3.6.1.2.1.25.2.1.4"      # hrStorageFixedDisk


class WindowsSNMPCollector(AbstractCollector):
    """Collect Windows server metrics via SNMPv2c."""

    def __init__(self, target_config: dict) -> None:
        self.target_id: str = target_config["id"]
        self.hostname: str = target_config["hostname"]
        self.community: str = target_config.get("snmp_community", "public")
        self.port: int = target_config.get("snmp_port", 161)
        self.display_name: str = target_config.get("display_name", self.target_id)

    # ── Public interface ─────────────────────────────────────────────────────

    def collect(self) -> list[WindowsServerMetric]:
        try:
            metric = WindowsServerMetric(
                source_id=self.target_id,
                source_type="windows_server",
                hostname=self.hostname,
                collection_method="snmp",
            )
            metric.cpu_usage_percent = self._get_cpu()
            ram_total, ram_used = self._get_memory()
            metric.ram_total_gb = ram_total
            metric.ram_used_gb = ram_used
            if ram_total > 0:
                metric.ram_usage_percent = round(ram_used / ram_total * 100, 2)
            metric.disks = self._get_disks()
            metric.uptime_seconds = self._get_uptime()
            metric.os_version = self._get_sys_descr()
            metric.reachable = True
            logger.info("snmp_collected target=%s cpu=%.1f%% ram=%.1f%%",
                        self.target_id, metric.cpu_usage_percent, metric.ram_usage_percent)
            return [metric]
        except Exception as exc:
            logger.error("snmp_collection_failed target=%s error=%s", self.target_id, exc)
            return [WindowsServerMetric(
                source_id=self.target_id,
                source_type="windows_server",
                hostname=self.hostname,
                collection_method="snmp",
                reachable=False,
            )]

    # ── Private helpers ──────────────────────────────────────────────────────

    def _transport(self) -> UdpTransportTarget:
        return UdpTransportTarget((self.hostname, self.port), timeout=5, retries=1)

    def _community(self) -> CommunityData:
        return CommunityData(self.community, mpModel=1)  # mpModel=1 → SNMPv2c

    def _walk(self, oid: str) -> list[tuple[str, Any]]:
        """Walk an OID table. Returns list of (oid_str, value) tuples."""
        results = []
        for error_indication, error_status, _, var_binds in nextCmd(
            SnmpEngine(),
            self._community(),
            self._transport(),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
            lexicographicMode=False,
        ):
            if error_indication or error_status:
                break
            for var_bind in var_binds:
                results.append((str(var_bind[0]), var_bind[1].prettyPrint()))
        return results

    def _get(self, oid: str) -> str | None:
        """GET a single scalar OID."""
        for error_indication, error_status, _, var_binds in getCmd(
            SnmpEngine(),
            self._community(),
            self._transport(),
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        ):
            if error_indication or error_status:
                return None
            return var_binds[0][1].prettyPrint()
        return None

    def _get_cpu(self) -> float:
        """Walk hrProcessorLoad table and return average across all CPUs."""
        rows = self._walk(OID_HR_PROCESSOR_LOAD)
        if not rows:
            return 0.0
        values = []
        for _, v in rows:
            try:
                values.append(float(v))
            except ValueError:
                pass
        return round(sum(values) / len(values), 2) if values else 0.0

    def _get_memory(self) -> tuple[float, float]:
        """
        Walk hrStorageTable. Find entry with type hrStorageRam.
        Returns (total_gb, used_gb).
        """
        types = dict(self._walk(OID_HR_STORAGE_TYPE))
        descrs = dict(self._walk(OID_HR_STORAGE_DESCR))
        units = dict(self._walk(OID_HR_STORAGE_ALLOC_UNITS))
        sizes = dict(self._walk(OID_HR_STORAGE_SIZE))
        useds = dict(self._walk(OID_HR_STORAGE_USED))

        for oid_str, type_val in types.items():
            # Match by OID suffix to find corresponding row fields
            idx = oid_str.rsplit(".", 1)[-1]
            if STORAGE_TYPE_RAM in type_val or "Ram" in descrs.get(
                f"{OID_HR_STORAGE_DESCR}.{idx}", ""
            ):
                try:
                    unit = int(units.get(f"{OID_HR_STORAGE_ALLOC_UNITS}.{idx}", 1))
                    size = int(sizes.get(f"{OID_HR_STORAGE_SIZE}.{idx}", 0))
                    used = int(useds.get(f"{OID_HR_STORAGE_USED}.{idx}", 0))
                    total_gb = round(unit * size / (1024 ** 3), 2)
                    used_gb = round(unit * used / (1024 ** 3), 2)
                    return total_gb, used_gb
                except (ValueError, TypeError):
                    pass
        return 0.0, 0.0

    def _get_disks(self) -> list[DiskMetric]:
        """Walk hrStorageTable and return one DiskMetric per fixed disk."""
        types = dict(self._walk(OID_HR_STORAGE_TYPE))
        descrs = dict(self._walk(OID_HR_STORAGE_DESCR))
        units = dict(self._walk(OID_HR_STORAGE_ALLOC_UNITS))
        sizes = dict(self._walk(OID_HR_STORAGE_SIZE))
        useds = dict(self._walk(OID_HR_STORAGE_USED))

        disks = []
        for oid_str, type_val in types.items():
            if STORAGE_TYPE_DISK not in type_val and "Fixed" not in type_val:
                continue
            idx = oid_str.rsplit(".", 1)[-1]
            try:
                unit = int(units.get(f"{OID_HR_STORAGE_ALLOC_UNITS}.{idx}", 1))
                size = int(sizes.get(f"{OID_HR_STORAGE_SIZE}.{idx}", 0))
                used = int(useds.get(f"{OID_HR_STORAGE_USED}.{idx}", 0))
                if size == 0:
                    continue
                total_gb = round(unit * size / (1024 ** 3), 2)
                used_gb = round(unit * used / (1024 ** 3), 2)
                usage_pct = round(used_gb / total_gb * 100, 2) if total_gb > 0 else 0.0
                drive = descrs.get(f"{OID_HR_STORAGE_DESCR}.{idx}", f"disk-{idx}")
                disks.append(DiskMetric(
                    drive_letter=drive,
                    total_gb=total_gb,
                    used_gb=used_gb,
                    usage_percent=usage_pct,
                ))
            except (ValueError, TypeError):
                pass
        return disks

    def _get_uptime(self) -> int:
        """Return system uptime in seconds from sysUpTime (centiseconds)."""
        raw = self._get(OID_SYS_UPTIME)
        if raw is None:
            return 0
        try:
            # sysUpTime is in centiseconds (hundredths of a second)
            centiseconds = int(raw.split(" ")[0].replace(",", ""))
            return centiseconds // 100
        except (ValueError, IndexError):
            return 0

    def _get_sys_descr(self) -> str:
        raw = self._get(OID_SYS_DESCR)
        return raw or ""
