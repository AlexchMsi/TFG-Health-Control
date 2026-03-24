from fastapi import APIRouter, Query, Request

from ..services.influx_query import InfluxQueryService

router = APIRouter()


def _svc(request: Request) -> InfluxQueryService:
    return InfluxQueryService(
        request.app.state.influx,
        request.app.state.bucket,
        request.app.state.org,
    )


@router.get("/", summary="Latest health for all (or one) server")
async def get_servers(
    request: Request,
    source_id: str | None = Query(default=None, description="Filter by server source_id"),
):
    return _svc(request).get_servers_latest(source_id)


@router.get("/disks", summary="Latest disk usage for all servers")
async def get_disks(
    request: Request,
    source_id: str | None = Query(default=None),
):
    return _svc(request).get_disks_latest(source_id)


@router.get("/services", summary="Latest service status for all servers")
async def get_services(
    request: Request,
    source_id: str | None = Query(default=None),
):
    return _svc(request).get_services_latest(source_id)


@router.get("/{source_id}/history", summary="CPU/RAM history for a specific server")
async def get_server_history(
    request: Request,
    source_id: str,
    range_minutes: int = Query(default=1440, ge=1, le=10080,
                               description="Time range in minutes (default 24h)"),
):
    return _svc(request).get_server_history(source_id, range_minutes)
