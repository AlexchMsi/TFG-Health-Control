import importlib
import sys
import types

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
FastAPI = fastapi.FastAPI
TestClient = testclient.TestClient


class FakeInfluxQueryService:
    calls = []

    def __init__(self, client, bucket, org):
        self.client = client
        self.bucket = bucket
        self.org = org

    def get_servers_latest(self, source_id=None):
        self.calls.append(("servers", source_id, self.bucket, self.org))
        return [{"kind": "server", "source_id": source_id}]

    def get_disks_latest(self, source_id=None):
        self.calls.append(("disks", source_id))
        return [{"kind": "disk", "source_id": source_id}]

    def get_services_latest(self, source_id=None):
        self.calls.append(("services", source_id))
        return [{"kind": "service", "source_id": source_id}]

    def get_server_history(self, source_id, range_minutes):
        self.calls.append(("history", source_id, range_minutes))
        return [{"kind": "history", "source_id": source_id, "range_minutes": range_minutes}]

    def get_esxi_hosts_latest(self):
        self.calls.append(("hosts",))
        return [{"kind": "host"}]

    def get_vms_latest(self, esxi_host=None, power_state=None):
        self.calls.append(("vms", esxi_host, power_state))
        return [{"kind": "vm", "esxi_host": esxi_host, "power_state": power_state}]

    def get_siemens_plcs_latest(self, source_id=None, plant=None):
        self.calls.append(("plcs", source_id, plant))
        return [{"kind": "plc", "source_id": source_id, "plant": plant}]


@pytest.fixture
def client(monkeypatch):
    influx = types.ModuleType("api.src.services.influx_query")
    influx.InfluxQueryService = FakeInfluxQueryService
    monkeypatch.setitem(sys.modules, "api.src.services.influx_query", influx)
    for name in [
        "api.src.routers.health",
        "api.src.routers.servers",
        "api.src.routers.vmware",
        "api.src.routers.plcs",
    ]:
        sys.modules.pop(name, None)

    health = importlib.import_module("api.src.routers.health")
    servers = importlib.import_module("api.src.routers.servers")
    vmware = importlib.import_module("api.src.routers.vmware")
    plcs = importlib.import_module("api.src.routers.plcs")
    app = FastAPI()
    app.state.influx = object()
    app.state.bucket = "bucket1"
    app.state.org = "org1"
    app.include_router(health.router, prefix="/health")
    app.include_router(servers.router, prefix="/metrics/servers")
    app.include_router(vmware.router, prefix="/metrics/vmware")
    app.include_router(plcs.router, prefix="/metrics/plcs")
    FakeInfluxQueryService.calls = []
    return TestClient(app)


def test_health_liveness(client):
    assert client.get("/health/").json() == {"status": "ok", "service": "health-api"}


def test_server_routes_delegate_to_service(client):
    assert client.get("/metrics/servers/?source_id=srv1").json() == [{"kind": "server", "source_id": "srv1"}]
    assert client.get("/metrics/servers/disks?source_id=srv1").json() == [{"kind": "disk", "source_id": "srv1"}]
    assert client.get("/metrics/servers/services?source_id=srv1").json() == [{"kind": "service", "source_id": "srv1"}]
    assert client.get("/metrics/servers/srv1/history?range_minutes=30").json() == [{"kind": "history", "source_id": "srv1", "range_minutes": 30}]
    assert FakeInfluxQueryService.calls[0] == ("servers", "srv1", "bucket1", "org1")


def test_vmware_routes_delegate_to_service(client):
    assert client.get("/metrics/vmware/hosts").json() == [{"kind": "host"}]
    assert client.get("/metrics/vmware/vms?esxi_host=esx1&power_state=poweredOn").json() == [
        {"kind": "vm", "esxi_host": "esx1", "power_state": "poweredOn"}
    ]
    assert ("vms", "esx1", "poweredOn") in FakeInfluxQueryService.calls


def test_plc_route_delegates_to_service(client):
    assert client.get("/metrics/plcs/siemens?source_id=plc1&plant=Madrid").json() == [
        {"kind": "plc", "source_id": "plc1", "plant": "Madrid"}
    ]
    assert ("plcs", "plc1", "Madrid") in FakeInfluxQueryService.calls



def test_server_history_validates_range(client):
    assert client.get("/metrics/servers/srv1/history?range_minutes=0").status_code == 422
