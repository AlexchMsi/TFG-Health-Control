from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from influxdb_client import InfluxDBClient

from shared.config.settings import Settings

from .database import create_db_and_tables
from .routers import health, servers, vmware
from .routers import config as config_router
from .routers import plcs

_UI_HTML = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    app.state.influx = InfluxDBClient(
        url=settings.influxdb_url,
        token=settings.influxdb_admin_token,
        org=settings.influxdb_org,
    )
    app.state.bucket = settings.influxdb_bucket
    app.state.org = settings.influxdb_org
    yield
    app.state.influx.close()


app = FastAPI(
    title="GEA Control System Health API",
    version="0.1.0",
    description=(
        "Vendor-neutral, real-time health monitoring for industrial OT environments. "
        "Exposes metrics collected from Windows servers, VMware ESXi hosts/VMs, "
        "and industrial PLCs."
    ),
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(servers.router, prefix="/metrics/servers", tags=["Servers"])
app.include_router(vmware.router, prefix="/metrics/vmware", tags=["VMware"])
app.include_router(config_router.router, prefix="/config", tags=["Config"])
app.include_router(plcs.router, prefix="/metrics/plcs", tags=["PLCs"])


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui():
    return _UI_HTML
