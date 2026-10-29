"""
Snap7 collector for Siemens S7-1500 / S7-1200 / S7-300 PLCs.

Uses SZL (System Zustands Liste) reads — no DB tags required, reads
system information directly from the CPU via S7Comm port 102.

SZL IDs used:
    0x0011  — hardware/firmware/serial (get_cpu_info() wrapper)
    0x0019  — CPU operating state (RUN/STOP/STARTUP)
    0x0090  — memory usage (load memory + work memory)
    0x0074  — diagnostic buffer (last errors)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import snap7
from snap7.util import get_int, get_dword

from shared.models.siemens import SiemensPlcMetric, SiemensDiagnosticEvent

logger = logging.getLogger(__name__)

# CPU state codes from SZL 0x0019
_CPU_STATE_MAP = {
    0x08: "RUN",
    0x04: "STOP",
    0x02: "STARTUP",
    0x10: "HOLD",
    0x00: "UNKNOWN",
}


class Snap7Collector:
    """
    Collects PLC health metrics via Snap7 (S7Comm, port 102).

    target dict keys used:
        snap7_host  : str  — PLC IP address
        snap7_rack  : int  — rack number (usually 0 for S7-1500)
        snap7_slot  : int  — slot number (usually 1 for S7-1500, 2 for S7-300)
        plc_name    : str
        plant       : str
        source_id   : str
        timeout_seconds : int  (default 10)
    """

    def __init__(self, target: dict) -> None:
        cfg = target["config"]
        self._host: str = cfg["snap7_host"]
        self._rack: int = cfg.get("snap7_rack", 0)
        self._slot: int = cfg.get("snap7_slot", 1)
        self._plc_name: str = target["display_name"]
        self._plant: str = target["plant"]
        self._source_id: str = target["id"]
        self._timeout: int = cfg.get("timeout_seconds", 10)

    def collect(self) -> SiemensPlcMetric:
        client = snap7.client.Client()
        metric = SiemensPlcMetric(
            source_id=self._source_id,
            source_type="siemens_plc",
            plc_name=self._plc_name,
            plant=self._plant,
            collection_method="snap7",
            collected_at=datetime.now(timezone.utc),
        )
        try:
            client.set_connection_type(1)  # PG connection — read-only access
            client.connect(self._host, self._rack, self._slot)

            self._read_cpu_info(client, metric)
            self._read_cpu_state(client, metric)
            self._read_memory(client, metric)
            self._read_diagnostics(client, metric)

            # reachable == the S7Comm connection and SZL reads worked; a PLC in
            # STOP is still reachable. cpu_state carries the operating mode.
            metric.reachable = True
        except Exception as exc:
            logger.error("Snap7 collect error [%s]: %s", self._source_id, exc)
            metric.reachable = False
            metric.last_error_text = str(exc)
        finally:
            try:
                client.disconnect()
            except Exception:
                pass
        return metric

    def _read_cpu_info(self, client: snap7.client.Client, metric: SiemensPlcMetric) -> None:
        try:
            info = client.get_cpu_info()
            metric.model = info.ModuleTypeName.decode("utf-8", errors="replace").strip("\x00")
            metric.firmware = info.SWVersion.decode("utf-8", errors="replace").strip("\x00")
            metric.serial_number = info.SerialNumber.decode("utf-8", errors="replace").strip("\x00")
        except Exception as exc:
            logger.debug("Snap7 get_cpu_info failed [%s]: %s", self._source_id, exc)

    def _read_cpu_state(self, client: snap7.client.Client, metric: SiemensPlcMetric) -> None:
        try:
            state = client.get_cpu_state()
            # snap7 returns cpu_state as string "S7CpuStatusRun" etc.
            state_str = str(state).upper()
            if "RUN" in state_str:
                metric.cpu_state = "RUN"
                metric.cpu_state_code = 0x08
            elif "STOP" in state_str:
                metric.cpu_state = "STOP"
                metric.cpu_state_code = 0x04
            else:
                metric.cpu_state = "UNKNOWN"
                metric.cpu_state_code = 0x00
        except Exception as exc:
            logger.debug("Snap7 get_cpu_state failed [%s]: %s", self._source_id, exc)

    def _read_memory(self, client: snap7.client.Client, metric: SiemensPlcMetric) -> None:
        try:
            # SZL 0x0090 index 0 — memory usage
            szl = client.read_szl(0x0090, 0)
            if szl and len(szl.list) > 0:
                entry = szl.list[0]
                # Byte offsets from Siemens documentation for SZL 0x0090
                load_used = get_dword(entry, 2)
                load_total = get_dword(entry, 6)
                work_used = get_dword(entry, 10)
                work_total = get_dword(entry, 14)
                if load_total:
                    metric.load_memory_used_percent = round(load_used / load_total * 100, 1)
                if work_total:
                    metric.work_memory_used_percent = round(work_used / work_total * 100, 1)
        except Exception as exc:
            logger.debug("Snap7 SZL 0x0090 failed [%s]: %s", self._source_id, exc)

    def _read_diagnostics(self, client: snap7.client.Client, metric: SiemensPlcMetric) -> None:
        try:
            szl = client.read_szl(0x0074, 0)
            if szl and len(szl.list) > 0:
                entry = szl.list[0]
                event_id = get_int(entry, 0)
                metric.last_error_code = event_id
        except Exception as exc:
            logger.debug("Snap7 SZL 0x0074 failed [%s]: %s", self._source_id, exc)
