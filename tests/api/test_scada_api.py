import importlib
import sys
import types

import pytest

from tests.api.test_influx_query_service import FakeClient, FakeQueryApi


@pytest.fixture
def service_module(monkeypatch):
    influx = types.ModuleType("influxdb_client")
    influx.InfluxDBClient = object
    monkeypatch.setitem(sys.modules, "influxdb_client", influx)
    sys.modules.pop("api.src.services.influx_query", None)
    return importlib.import_module("api.src.services.influx_query")


def test_scada_latest_flux(service_module):
    query_api = FakeQueryApi()
    svc = service_module.InfluxQueryService(FakeClient(query_api), "bucket1", "org1")

    svc.get_scada_latest(source_id="s1", scada_type="Ignition", tag_name="Temp")


    flux = query_api.calls[0]["flux"]
    assert 'r._measurement == "scada_tag_health"' in flux
    assert 'r["source_id"] == "s1"' in flux
    assert 'r["scada_type"] == "Ignition"' in flux
    assert 'r["tag_name"] == "Temp"' in flux
    assert 'pivot(rowKey: ["source_id", "scada_type", "tag_name"]' in flux


def test_scada_history_flux(service_module):
    query_api = FakeQueryApi()
    svc = service_module.InfluxQueryService(FakeClient(query_api), "bucket1", "org1")

    svc.get_scada_history(source_id="s1", tag_name="Temp", range_minutes=60)

    flux = query_api.calls[0]["flux"]
    assert "range(start: -60m)" in flux
    assert 'r._measurement == "scada_tag_health"' in flux
    assert 'r["source_id"] == "s1"' in flux
    assert 'r["tag_name"] == "Temp"' in flux
