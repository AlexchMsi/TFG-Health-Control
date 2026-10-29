import importlib
import sys
import types
from datetime import datetime, timezone

import pytest


class FakeWritePrecision:
    S = "s"


class FakeInfluxDBError(Exception):
    pass


class FakePoint:
    def __init__(self, measurement):
        self.measurement = measurement
        self.tags = {}
        self.fields = {}
        self.timestamp = None
        self.precision = None

    def tag(self, key, value):
        self.tags[key] = value
        return self

    def field(self, key, value):
        self.fields[key] = value
        return self

    def time(self, timestamp, precision):
        self.timestamp = timestamp
        self.precision = precision
        return self


class FakeWriteApi:
    def __init__(self):
        self.calls = []
        self.closed = False
        self.raise_on_write = None

    def write(self, **kwargs):
        if self.raise_on_write:
            raise self.raise_on_write
        self.calls.append(kwargs)

    def close(self):
        self.closed = True


class FakeInfluxDBClient:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.write_api_instance = FakeWriteApi()
        self.closed = False
        FakeInfluxDBClient.instances.append(self)

    def write_api(self, write_options):
        self.write_options = write_options
        return self.write_api_instance

    def close(self):
        self.closed = True


@pytest.fixture
def writer_module(monkeypatch):
    FakeInfluxDBClient.instances = []

    influxdb_client = types.ModuleType("influxdb_client")
    influxdb_client.InfluxDBClient = FakeInfluxDBClient
    influxdb_client.Point = FakePoint
    influxdb_client.WritePrecision = FakeWritePrecision

    client = types.ModuleType("influxdb_client.client")
    write_api = types.ModuleType("influxdb_client.client.write_api")
    write_api.SYNCHRONOUS = "sync"
    exceptions = types.ModuleType("influxdb_client.client.exceptions")
    exceptions.InfluxDBError = FakeInfluxDBError

    monkeypatch.setitem(sys.modules, "influxdb_client", influxdb_client)
    monkeypatch.setitem(sys.modules, "influxdb_client.client", client)
    monkeypatch.setitem(sys.modules, "influxdb_client.client.write_api", write_api)
    monkeypatch.setitem(sys.modules, "influxdb_client.client.exceptions", exceptions)

    sys.modules.pop("shared.influx.writer", None)
    return importlib.import_module("shared.influx.writer")


def test_write_point_builds_point_with_seconds_precision(writer_module):
    writer = writer_module.InfluxWriter("http://influx", "token", "org", "bucket")
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    writer.write_point(
        measurement="server",
        tags={"source_id": "srv-1", "none": None},
        fields={"reachable": int(True), "cpu": 12.5, "skip": None},
        timestamp=timestamp,
    )

    client = FakeInfluxDBClient.instances[0]
    call = client.write_api_instance.calls[0]
    point = call["record"]

    assert client.kwargs == {"url": "http://influx", "token": "token", "org": "org"}
    assert client.write_options == "sync"
    assert call["bucket"] == "bucket"
    assert call["org"] == "org"
    assert point.measurement == "server"
    assert point.tags == {"source_id": "srv-1"}
    assert point.fields == {"reachable": 1, "cpu": 12.5}
    assert point.timestamp == timestamp
    assert point.precision == FakeWritePrecision.S


def test_write_point_wraps_influx_errors(writer_module):
    writer = writer_module.InfluxWriter("url", "token", "org", "bucket")
    FakeInfluxDBClient.instances[0].write_api_instance.raise_on_write = FakeInfluxDBError("boom")

    with pytest.raises(writer_module.WriteError, match=r"InfluxDB write failed for \[measurement\]"):
        writer.write_point("measurement", {}, {})


def test_write_batch_builds_all_points_with_seconds_precision(writer_module):
    writer = writer_module.InfluxWriter("url", "token", "org", "bucket")
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    writer.write_batch([
        {
            "measurement": "server",
            "tags": {"source_id": "srv-1"},
            "fields": {"reachable": int(False), "skip": None},
            "timestamp": timestamp,
        },
        {"measurement": "vm", "tags": {}, "fields": {"reachable": 1}},
    ])

    record = FakeInfluxDBClient.instances[0].write_api_instance.calls[0]["record"]

    assert [point.measurement for point in record] == ["server", "vm"]
    assert record[0].fields == {"reachable": 0}
    assert record[0].timestamp == timestamp
    assert all(point.precision == FakeWritePrecision.S for point in record)


def test_close_closes_api_and_client(writer_module):
    writer = writer_module.InfluxWriter("url", "token", "org", "bucket")
    client = FakeInfluxDBClient.instances[0]

    writer.close()

    assert client.write_api_instance.closed is True
    assert client.closed is True
