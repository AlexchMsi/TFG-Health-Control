import importlib
import json
import sys
import types

import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
FastAPI = fastapi.FastAPI
TestClient = testclient.TestClient


class FakeRecord:
    values = {"source_id": "tag1", "quality": "bad"}


class FakeTable:
    records = [FakeRecord()]


class FakeQueryApi:
    def __init__(self):
        self.queries = []

    def query(self, query, org):
        self.queries.append((query, org))
        return [FakeTable()]


class FakeInflux:
    def __init__(self):
        self.query_api_obj = FakeQueryApi()

    def query_api(self):
        return self.query_api_obj


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"response": '{"summary":"ok","risk_level":"low","recommendations":[]}'}


def _fake_async_client_cls(calls):
    class FakeAsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse()

    return FakeAsyncClient


def test_latest_reads_recommendations_file(monkeypatch, tmp_path):
    sys.modules.pop("api.src.routers.recommendations", None)
    module = importlib.import_module("api.src.routers.recommendations")
    path = tmp_path / "recommendations.json"
    path.write_text(json.dumps([{"summary": "ok"}]), encoding="utf-8")
    monkeypatch.setattr(module, "RECOMMENDATIONS_PATH", path)
    app = FastAPI()
    app.include_router(module.router, prefix="/recommendations")

    assert TestClient(app).get("/recommendations/latest").json() == [{"summary": "ok"}]


def test_analyze_queries_scada_and_calls_ollama(monkeypatch):
    sys.modules.pop("api.src.routers.recommendations", None)
    module = importlib.import_module("api.src.routers.recommendations")
    calls = []
    monkeypatch.setattr(module.httpx, "AsyncClient", _fake_async_client_cls(calls))
    app = FastAPI()
    app.state.influx = FakeInflux()
    app.state.bucket = "bucket1"
    app.state.org = "org1"
    app.state.settings = types.SimpleNamespace(ollama_url="http://ollama:11434", ollama_model="llama3.1:8b")
    app.include_router(module.router, prefix="/recommendations")

    response = TestClient(app).post("/recommendations/analyze")

    assert response.json()["summary"] == "ok"
    assert "scada_tag_health" in calls[0][1]["json"]["prompt"]
    assert any("scada_tag_health" in query for query, org in app.state.influx.query_api_obj.queries)
