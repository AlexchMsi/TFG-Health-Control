import importlib
import sys
import types

import pytest


class FakeRecord:
    def __init__(self, values):
        self.values = values


class FakeTable:
    def __init__(self, records):
        self.records = records


class FakeQueryApi:
    def __init__(self):
        self.calls = []
        self.tables = [FakeTable([FakeRecord({"source_id": "srv1", "reachable": 1})])]

    def query(self, flux, org):
        self.calls.append({"flux": flux, "org": org})
        return self.tables


class FakeClient:
    def __init__(self, query_api):
        self._query_api = query_api

    def query_api(self):
        return self._query_api


@pytest.fixture
def service_module(monkeypatch):
    influx = types.ModuleType("influxdb_client")
    influx.InfluxDBClient = object
    monkeypatch.setitem(sys.modules, "influxdb_client", influx)
    sys.modules.pop("api.src.services.influx_query", None)
    return importlib.import_module("api.src.services.influx_query")


@pytest.fixture
def service(service_module):
    query_api = FakeQueryApi()
    svc = service_module.InfluxQueryService(FakeClient(query_api), "bucket1", "org1")
    svc.query_api = query_api
    return svc


def test_execute_flattens_record_values(service):
    assert service.get_servers_latest() == [{"source_id": "srv1", "reachable": 1}]
    assert service.query_api.calls[0]["org"] == "org1"


@pytest.mark.parametrize(
    "method,args,expected",
    [
        ("get_servers_latest", {"source_id": "srv1"}, ["server_health", 'r["source_id"] == "srv1"', "pivot"]),
        ("get_disks_latest", {"source_id": "srv1"}, ["disk_health", 'r["source_id"] == "srv1"', "drive_letter"]),
        ("get_services_latest", {"source_id": "srv1"}, ["service_health", 'r["source_id"] == "srv1"', "service_name"]),
        ("get_server_history", {"source_id": "srv1", "range_minutes": 60}, ["server_health", "range(start: -60m)", "ram_usage_percent"]),
        ("get_esxi_hosts_latest", {}, ["esxi_health", "range(start: -15m)", "hostname"]),
        ("get_vms_latest", {"esxi_host": "esx1", "power_state": "poweredOn"}, ["vm_health", 'r["esxi_host"] == "esx1"', 'r["power_state"] == "poweredOn"']),
        ("get_siemens_plcs_latest", {"source_id": "plc1", "plant": "Madrid"}, ["siemens_plc_health", 'r["source_id"] == "plc1"', 'r["plant"] == "Madrid"']),
    ],
)
def test_query_builders_use_expected_measurements_filters_and_bucket(service, method, args, expected):
    getattr(service, method)(**args)

    flux = service.query_api.calls[-1]["flux"]
    assert 'from(bucket: "bucket1")' in flux
    for text in expected:
        assert text in flux


def test_string_params_are_escaped(service):
    service.get_scada_latest(tag_name='x" or true) //')

    flux = service.query_api.calls[-1]["flux"]
    assert 'r["tag_name"] == "x\\" or true) //"' in flux
    assert '== "x" or true' not in flux


def test_backslashes_are_escaped(service):
    service.get_servers_latest(source_id='srv\\"1')

    flux = service.query_api.calls[-1]["flux"]
    assert 'r["source_id"] == "srv\\\\\\"1"' in flux


def test_get_latest_by_measurement_builds_pivoted_query(service):
    service.get_latest_by_measurement("scada_tag_health")

    flux = service.query_api.calls[-1]["flux"]
    assert 'r._measurement == "scada_tag_health"' in flux
    assert 'pivot(rowKey: ["source_id"]' in flux
    assert "last()" in flux
