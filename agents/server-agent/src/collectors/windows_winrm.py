"""
Windows WinRM Collector — enhanced collection path.

Uses PowerShell remoting over WinRM to collect:
- CPU, RAM, disk (same as SNMP but with more detail)
- Critical service status (not available via standard SNMP MIBs)
- NTP clock offset (w32tm /query /status)

Requires WinRM enabled on the target:
  Enable-PSRemoting -Force
  Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "<agent IP>"
"""
from __future__ import annotations

import json
import logging
import re

import winrm

from .base import AbstractCollector
from shared.models.server import DiskMetric, ServiceStatus, WindowsServerMetric

logger = logging.getLogger(__name__)

# PowerShell script executed on the remote host.
# Outputs a single JSON object with all metrics.
_PS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1).CounterSamples[0].CookedValue

    $disks = Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } |
        Select-Object @{N='Drive';E={$_.Name+':'}},
                      @{N='TotalGB';E={[math]::Round(($_.Used + $_.Free) / 1GB, 2)}},
                      @{N='UsedGB';E={[math]::Round($_.Used / 1GB, 2)}},
                      @{N='FreeGB';E={[math]::Round($_.Free / 1GB, 2)}}

    $ntpRaw = (w32tm /query /status 2>&1) -join "`n"
    $ntpOffset = if ($ntpRaw -match 'Last Successful Sync Time.*') { 'synced' } else { 'unknown' }
    $offsetMs = 0
    if ($ntpRaw -match 'RMS Offset:\s+([\d.]+)\s*s') { $offsetMs = [math]::Round([double]$matches[1] * 1000, 2) }
    $ntpServer = if ($ntpRaw -match 'Source:\s+(.+)') { $matches[1].Trim() } else { '' }

    # __CRITICAL_SERVICES__ is replaced client-side with a PS array literal:
    # remote env vars are not propagated by run_ps, so interpolation is the
    # only way the list reaches this script.
    $svcNames = @(__CRITICAL_SERVICES__)
    $services = if ($svcNames.Count -gt 0) {
        Get-Service -Name $svcNames -ErrorAction SilentlyContinue |
            Select-Object Name, DisplayName,
                          @{N='State';E={$_.Status.ToString()}},
                          @{N='StartMode';E={$_.StartType.ToString()}}
    } else { @() }

    @{
        Hostname     = $env:COMPUTERNAME
        OSVersion    = $os.Caption
        UptimeSecs   = [int]($os.LocalDateTime - $os.LastBootUpTime).TotalSeconds
        CPUPercent   = [math]::Round($cpu, 2)
        RAMTotalGB   = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
        RAMFreeGB    = [math]::Round($os.FreePhysicalMemory * 1KB / 1GB, 2)
        Disks        = $disks
        NTPOffsetMs  = $offsetMs
        NTPServer    = $ntpServer
        Services     = $services
    } | ConvertTo-Json -Depth 5
} catch {
    @{ Error = $_.Exception.Message } | ConvertTo-Json
}
"""


class WindowsWinRMCollector(AbstractCollector):
    """Collect Windows server metrics via WinRM / PowerShell remoting."""

    def __init__(self, target_config: dict) -> None:
        self.target_id: str = target_config["id"]
        self.hostname: str = target_config["hostname"]
        self.user: str = target_config.get("winrm_user", "")
        self.password: str = target_config.get("winrm_password", "")
        self.transport: str = target_config.get("winrm_transport", "ntlm")
        self.port: int = int(target_config.get("winrm_port", 5985))
        self.critical_services: list[str] = target_config.get("critical_services", [])
        self.display_name: str = target_config.get("display_name", self.target_id)

    def _build_script(self) -> str:
        svc_literal = ",".join(
            "'" + s.replace("'", "''") + "'" for s in self.critical_services if s
        )
        return _PS_SCRIPT.replace("__CRITICAL_SERVICES__", svc_literal)

    def collect(self) -> list[WindowsServerMetric]:
        try:
            scheme = "https" if self.port == 5986 else "http"
            session = winrm.Session(
                f"{scheme}://{self.hostname}:{self.port}/wsman",
                auth=(self.user, self.password),
                transport=self.transport,
                read_timeout_sec=30,
                operation_timeout_sec=25,
            )
            result = session.run_ps(self._build_script())
            if result.status_code != 0:
                raise RuntimeError(result.std_err.decode(errors="replace"))

            raw = json.loads(result.std_out.decode(errors="replace"))
            if "Error" in raw:
                raise RuntimeError(raw["Error"])

            metric = self._parse(raw)
            logger.info("winrm_collected target=%s cpu=%.1f%% ram=%.1f%%",
                        self.target_id, metric.cpu_usage_percent, metric.ram_usage_percent)
            return [metric]
        except Exception as exc:
            logger.error("winrm_collection_failed target=%s error=%s", self.target_id, exc)
            return [WindowsServerMetric(
                source_id=self.target_id,
                source_type="windows_server",
                hostname=self.hostname,
                collection_method="winrm",
                reachable=False,
            )]

    def _parse(self, raw: dict) -> WindowsServerMetric:
        ram_total = float(raw.get("RAMTotalGB", 0))
        ram_free = float(raw.get("RAMFreeGB", 0))
        ram_used = round(ram_total - ram_free, 2)
        ram_pct = round(ram_used / ram_total * 100, 2) if ram_total > 0 else 0.0

        disks = []
        for d in raw.get("Disks", []) or []:
            total = float(d.get("TotalGB", 0))
            used = float(d.get("UsedGB", 0))
            pct = round(used / total * 100, 2) if total > 0 else 0.0
            disks.append(DiskMetric(
                drive_letter=d.get("Drive", "?"),
                total_gb=total,
                used_gb=used,
                usage_percent=pct,
            ))

        services = []
        for s in raw.get("Services", []) or []:
            services.append(ServiceStatus(
                name=s.get("Name", ""),
                display_name=s.get("DisplayName", ""),
                state=s.get("State", "Unknown"),
                start_mode=s.get("StartMode", "Unknown"),
            ))

        return WindowsServerMetric(
            source_id=self.target_id,
            source_type="windows_server",
            hostname=raw.get("Hostname", self.hostname),
            os_version=raw.get("OSVersion", ""),
            collection_method="winrm",
            cpu_usage_percent=float(raw.get("CPUPercent", 0)),
            ram_total_gb=ram_total,
            ram_used_gb=ram_used,
            ram_usage_percent=ram_pct,
            uptime_seconds=int(raw.get("UptimeSecs", 0)),
            clock_offset_ms=raw.get("NTPOffsetMs"),
            ntp_server=raw.get("NTPServer") or None,
            disks=disks,
            services=services,
            reachable=True,
        )
