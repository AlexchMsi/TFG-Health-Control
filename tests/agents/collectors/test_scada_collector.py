import asyncio
import sys

from shared.models.scada import ScadaTagMetric
from tests.agents.collectors.import_helpers import ROOT, load_module


def test_split_value_maps_supported_types():
    module = load_module("opcua_collector", ROOT / "agents" / "scada-agent" / "src" / "collectors" / "opcua_collector.py", "scada_collectors")

    assert module._split_value(1.5) == (1.5, None, None)
    assert module._split_value(True) == (None, None, True)
    assert module._split_value("RUN") == (None, "RUN", None)


def test_collect_returns_bad_metric_on_total_failure():
    module = load_module("opcua_collector", ROOT / "agents" / "scada-agent" / "src" / "collectors" / "opcua_collector.py", "scada_collectors")

    async def fail(self):
        raise RuntimeError("cannot connect")

    module.OpcuaScadaCollector._collect_async = fail
    collector = module.OpcuaScadaCollector({
        "id": "scada1",
        "opcua_url": "opc.tcp://host:4840",
        "scada_type": "auto",
        "tags": [{"name": "Temp", "node_id": "ns=2;s=Temp"}],
    })

    metrics = collector.collect()

    assert len(metrics) == 1
    assert isinstance(metrics[0], ScadaTagMetric)
    assert metrics[0].reachable is False
    assert metrics[0].quality == "BAD"
    assert metrics[0].value_float is None
    assert metrics[0].last_error_text == "cannot connect"
