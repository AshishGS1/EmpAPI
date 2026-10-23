"""/health: liveness (process is up) and readiness (dependencies are reachable)."""



from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from empapi.exceptions import ApiError
from empapi.models.common import HealthStatus
from empapi.utils.logging_config import get_logger

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger("health")


@router.get("/live", response_model=HealthStatus)
async def live() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/ready", response_model=HealthStatus, responses={503: {"model": HealthStatus}})
async def ready(request: Request):
    checks: dict[str, str] = {}

    checks["mcp"] = "ok" if await request.app.state.gateway.ping() else "unreachable"
    try:
        await request.app.state.user_store.ping()
        checks["database"] = "ok"
    except ApiError:
        checks["database"] = "unreachable"
    except Exception:  # a probe must answer, whatever the store raises
        logger.warning("Readiness database check failed", exc_info=True)
        checks["database"] = "unreachable"

    healthy = all(value == "ok" for value in checks.values())
    body = HealthStatus(status="ok" if healthy else "unavailable", checks=checks)
    return JSONResponse(body.model_dump(), status_code=200 if healthy else 503)
