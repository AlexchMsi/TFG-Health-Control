from contextlib import asynccontextmanager

from fastapi import FastAPI
from influxdb_client import InfluxDBClient

from shared.config.settings import Settings

from .routers import health, servers, vmware

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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
