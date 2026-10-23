"""/employees: details for one employee, and search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from empapi.deps import AuthenticatedUser, get_gateway, require_scopes
from empapi.mcp.gateway import McpGateway
from empapi.routers.responses import ERROR_RESPONSES
from empapi.models.employee import EmployeeDetails, EmployeeSearchResult
from empapi.security.scopes import SCOPE_EMPLOYEES_READ
from empapi.services import employee_service
from empapi.routers.responses import SEARCH_MAX_LIMIT, FILTER_MAX_LENGTH

router = APIRouter(prefix="/employees", tags=["employees"], responses=ERROR_RESPONSES)


@router.get(
    "/{employee_id}",
    response_model=EmployeeDetails,
    summary="Get one employee",
    description="Full record for one employee. The salary is null unless your role includes salary access.",
)
async def get_employee(
    employee_id: int = Path(ge=1, description="Numeric employee ID (e_id)"),
    user: AuthenticatedUser = Depends(require_scopes(SCOPE_EMPLOYEES_READ)),
    gateway: McpGateway = Depends(get_gateway),
) -> EmployeeDetails:
    return await employee_service.get_employee(gateway, user, employee_id)


@router.get(
    "",
    response_model=EmployeeSearchResult,
    summary="Search employees",
    description="Case-insensitive contains-search. Filters are combined with AND and at "
    "least one is required. No match returns an empty list, not an error.",
)
async def search_employees(
    name: str | None = Query(None, max_length=FILTER_MAX_LENGTH, description="Part of the name"),
    department: str | None = Query(
        None, max_length=FILTER_MAX_LENGTH, description="Part of the department name"
    ),
    job_title: str | None = Query(
        None, max_length=FILTER_MAX_LENGTH, description="Part of the job title"
    ),
    limit: int = Query(10, ge=1, le=SEARCH_MAX_LIMIT, description="Page size"),
    offset: int = Query(0, ge=0, description="Rows to skip, for paging"),
    user: AuthenticatedUser = Depends(require_scopes(SCOPE_EMPLOYEES_READ)),
    gateway: McpGateway = Depends(get_gateway),
) -> EmployeeSearchResult:
    return await employee_service.search_employees(
        gateway, user, name=name, department=department, job_title=job_title,
        limit=limit, offset=offset,
    )
