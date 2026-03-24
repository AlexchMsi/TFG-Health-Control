from fastapi import APIRouter, Query, Request

from ..services.influx_query import InfluxQueryService

router = APIRouter()


def _svc(request: Request) -> InfluxQueryService:
    return InfluxQueryService(
        request.app.state.influx,
        request.app.state.bucket,
        request.app.state.org,
    )


@router.get("/hosts", summary="Latest health for all ESXi hosts")
async def get_esxi_hosts(request: Request):
    return _svc(request).get_esxi_hosts_latest()


@router.get("/vms", summary="Latest health for all VMs")
async def get_vms(
    request: Request,
    esxi_host: str | None = Query(default=None, description="Filter VMs by ESXi host name"),
    power_state: str | None = Query(
        default=None,
        description="Filter by power state: poweredOn | poweredOff | suspended",
    ),
):
    return _svc(request).get_vms_latest(esxi_host, power_state)
