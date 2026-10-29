from fastapi import APIRouter, Query, Request

from ..services.influx_query import InfluxQueryService

router = APIRouter()


def _svc(request: Request) -> InfluxQueryService:
    return InfluxQueryService(request.app.state.influx, request.app.state.bucket, request.app.state.org)


@router.get("/", summary="Latest SCADA tag health")
async def get_scada_latest(
    request: Request,
    source_id: str | None = Query(default=None),
    scada_type: str | None = Query(default=None),
    tag_name: str | None = Query(default=None),
):
    return _svc(request).get_scada_latest(source_id=source_id, scada_type=scada_type, tag_name=tag_name)


@router.get("/{source_id}/history", summary="SCADA tag history")
async def get_scada_history(
    request: Request,
    source_id: str,
    tag_name: str | None = Query(default=None),
    range_minutes: int = Query(default=1440, ge=1, le=10080),
):
    return _svc(request).get_scada_history(source_id=source_id, tag_name=tag_name, range_minutes=range_minutes)
