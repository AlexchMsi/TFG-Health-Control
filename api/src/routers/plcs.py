from fastapi import APIRouter, Query, Request

from ..services.influx_query import InfluxQueryService

router = APIRouter()


def _svc(request: Request) -> InfluxQueryService:
    return InfluxQueryService(
        request.app.state.influx,
        request.app.state.bucket,
        request.app.state.org,
    )


@router.get("/siemens", summary="Latest health for all (or one) Siemens PLC")
async def get_siemens_plcs(
    request: Request,
    source_id: str | None = Query(default=None, description="Filter by PLC source_id"),
    plant: str | None = Query(default=None, description="Filter by plant name"),
):
    return _svc(request).get_siemens_plcs_latest(source_id=source_id, plant=plant)
