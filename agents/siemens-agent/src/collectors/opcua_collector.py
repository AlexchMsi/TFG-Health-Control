"""
OPC UA collector for Siemens S7-1500 PLCs.

Works with any OPC UA server that exposes standard ServerStatus nodes:
  - Ignition OPC-UA gateway
  - Siemens WinCC OPC UA server
  - S7-1500 native OPC UA server (firmware >= V2.0)

For S7-1500 native, extra device-specific nodes are read when available but
failures are handled gracefully — only ServerStatus.State is mandatory.
"""

import asyncio
import logging
from datetime import datetime, timezone

from asyncua import Client
from asyncua.common.node import Node

from shared.models.siemens import SiemensPlcMetric

logger = logging.getLogger(__name__)

# Standard OPC UA node IDs (namespace 0)
_SERVER_STATE_NODE = "ns=0;i=2259"   # 0=Running, 1=Failed, 2=NoConfig, 3=Suspended, 4=Shutdown, 5=Test, 6=CommunicationFault, 7=Unknown
_SERVER_TIME_NODE = "ns=0;i=2258"    # ServerStatus.CurrentTime

_OPC_STATE_MAP = {
    0: "RUN",
    1: "FAULT",
    2: "STOP",
    3: "STOP",
    4: "STOP",
    5: "RUN",
    6: "FAULT",
    7: "FAULT",
}


async def _read_node_safe(client: Client, node_id: str, default=None):
    try:
        node: Node = client.get_node(node_id)
        return await node.read_value()
    except Exception:
        return default


class OpcuaCollector:
    """
    Collects PLC health metrics over OPC UA.

    target dict keys used:
        opcua_url       : str  — "opc.tcp://10.10.5.50:4840"
        plc_name        : str  — used as tag in InfluxDB
        plant           : str
        source_id       : str
        timeout_seconds : int  (default 10)
    """

    def __init__(self, target: dict) -> None:
        self._url: str = target["config"]["opcua_url"]
        self._plc_name: str = target["display_name"]
        self._plant: str = target["plant"]
        self._source_id: str = target["id"]
        self._timeout: int = target["config"].get("timeout_seconds", 10)

    def collect(self) -> SiemensPlcMetric:
        """Synchronous entry point — runs the async logic in a new event loop."""
        try:
            return asyncio.run(self._collect_async())
        except Exception as exc:
            logger.error("OPC UA collect error [%s]: %s", self._source_id, exc)
            return SiemensPlcMetric(
                source_id=self._source_id,
                source_type="siemens_plc",
                plc_name=self._plc_name,
                plant=self._plant,
                collection_method="opcua",
                reachable=False,
                last_error_text=str(exc),
            )

    async def _collect_async(self) -> SiemensPlcMetric:
        metric = SiemensPlcMetric(
            source_id=self._source_id,
            source_type="siemens_plc",
            plc_name=self._plc_name,
            plant=self._plant,
            collection_method="opcua",
            collected_at=datetime.now(timezone.utc),
        )

        async with Client(url=self._url, timeout=self._timeout) as client:
            # Mandatory: server state
            state_code = await _read_node_safe(client, _SERVER_STATE_NODE, default=7)
            metric.cpu_state_code = int(state_code)
            metric.cpu_state = _OPC_STATE_MAP.get(metric.cpu_state_code, "FAULT")
            metric.reachable = metric.cpu_state == "RUN"

            # Optional: try to read Siemens-specific nodes (S7-1500 native server)
            # Module state — ns=3 path varies by PLC name; skip silently if not found
            # We attempt a few common patterns.
            for ns3_state_path in [
                "ns=3;s=DeviceSet/PLC_1/Resources/CPU/ProgramData",
                "ns=3;s=DataBlocksGlobal",
            ]:
                val = await _read_node_safe(client, ns3_state_path)
                if val is not None:
                    break  # found something — S7 native server

        return metric
