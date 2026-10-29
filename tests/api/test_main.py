import importlib
import sys
import types

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
TestClient = testclient.TestClient


@pytest.fixture
def client(monkeypatch):
    influx = types.ModuleType("influxdb_client")
    influx.InfluxDBClient = object
    monkeypatch.setitem(sys.modules, "influxdb_client", influx)
    sys.modules.pop("api.src.main", None)
    main = importlib.import_module("api.src.main")
    return TestClient(main.app)


def test_root_redirects_to_ui(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui"


def test_ui_health_and_openapi_still_work(client):
    assert "GEA Control System Health Status" in client.get("/ui").text
    assert client.get("/health/").json() == {"status": "ok", "service": "health-api"}
    assert client.get("/openapi.json").status_code == 200
