import pytest

fastapi = pytest.importorskip("fastapi")
testclient = pytest.importorskip("fastapi.testclient")
sqlmodel = pytest.importorskip("sqlmodel")
pool = pytest.importorskip("sqlmodel.pool")

FastAPI = fastapi.FastAPI
TestClient = testclient.TestClient
Session = sqlmodel.Session
SQLModel = sqlmodel.SQLModel
create_engine = sqlmodel.create_engine
StaticPool = pool.StaticPool

from api.src.database import get_session
from api.src.models.target import Target
from api.src.routers.config import router


def make_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def session_override():
        with Session(engine) as session:
            yield session

    app = FastAPI()
    app.dependency_overrides[get_session] = session_override
    app.include_router(router, prefix="/config")
    return TestClient(app)


def test_target_crud_round_trip():
    client = make_client()
    payload = {
        "id": "srv1",
        "plant": "Madrid",
        "agent_type": "server",
        "display_name": "Server 1",
        "enabled": True,
        "config": {"host": "10.0.0.1"},
    }

    created = client.post("/config/targets", json=payload)
    assert created.status_code == 201
    assert created.json()["config"] == {"host": "10.0.0.1"}
    assert client.post("/config/targets", json=payload).status_code == 409

    assert client.get("/config/targets/srv1").json()["display_name"] == "Server 1"
    assert client.get("/config/targets?agent_type=server").json()[0]["id"] == "srv1"
    assert client.get("/config/targets?agent_type=siemens").json() == []

    updated = client.put("/config/targets/srv1", json={"enabled": False, "config": {"host": "10.0.0.2"}})
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False
    assert updated.json()["config"] == {"host": "10.0.0.2"}

    assert client.delete("/config/targets/srv1").status_code == 204
    assert client.get("/config/targets/srv1").status_code == 404


def test_missing_target_update_and_delete_return_404():
    client = make_client()

    assert client.put("/config/targets/missing", json={"enabled": False}).status_code == 404
    assert client.delete("/config/targets/missing").status_code == 404
