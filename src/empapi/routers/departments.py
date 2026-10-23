"""/departments: statistics for all departments, or for one."""

from fastapi import APIRouter, Depends, Path, Query

from empapi.deps import AuthenticatedUser, get_gateway, require_scopes
from empapi.mcp.gateway import McpGateway
from empapi.routers.responses import ERROR_RESPONSES
from empapi.models.department import DepartmentStatistics, DepartmentStatisticsResult
from empapi.security.scopes import SCOPE_DEPARTMENTS_READ
from empapi.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"], responses=ERROR_RESPONSES)


@router.get(
    "/stats",
    response_model=DepartmentStatisticsResult,
    summary="Statistics for every department",
    description="Headcount, budget and (with salary access) salary figures per department.",
)
async def all_department_stats(
    include_inactive: bool = Query(False, description="Also list inactive departments"),
    user: AuthenticatedUser = Depends(require_scopes(SCOPE_DEPARTMENTS_READ)),
    gateway: McpGateway = Depends(get_gateway),
) -> DepartmentStatisticsResult:
    return await department_service.all_departments(
        gateway, user, include_inactive=include_inactive
    )


@router.get(
    "/{department_id}/stats",
    response_model=DepartmentStatistics,
    summary="Statistics for one department",
    description="404 if the department does not exist. Returned even if the department is inactive.",
)
async def department_by_id_stats(
    department_id: int = Path(ge=1, description="Numeric department ID"),
    user: AuthenticatedUser = Depends(require_scopes(SCOPE_DEPARTMENTS_READ)),
    gateway: McpGateway = Depends(get_gateway),
) -> DepartmentStatistics:
    return await department_service.department_by_id(gateway, user, department_id)
