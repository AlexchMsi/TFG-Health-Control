from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Liveness check")
async def liveness():
    return {"status": "ok", "service": "health-api"}
