"""Employee use cases: validate early, call the MCP tool, shape the result."""



from empapi.deps import AuthenticatedUser
from empapi.exceptions import InvalidRequestError
from empapi.mcp.gateway import McpGateway
from empapi.mcp.consts import TOOL_GET_EMPLOYEE, TOOL_SEARCH_EMPLOYEES
from empapi.models.employee import EmployeeDetails, EmployeeSearchResult
from empapi.security.scopes import SCOPE_EMPLOYEES_READ
from empapi.services._parse import parse_result


async def get_employee(
    gateway: McpGateway, user: AuthenticatedUser, employee_id: int
) -> EmployeeDetails:
    payload = await gateway.call_tool(
        TOOL_GET_EMPLOYEE,
        {"employee_id": employee_id},
        user_id=user.user_id,
        user_scopes=user.scopes,
        required_scopes=[SCOPE_EMPLOYEES_READ],
    )
    return parse_result(EmployeeDetails, TOOL_GET_EMPLOYEE, payload)


async def search_employees(
    gateway: McpGateway,
    user: AuthenticatedUser,
    *,
    name: str | None,
    department: str | None,
    job_title: str | None,
    limit: int,
    offset: int,
) -> EmployeeSearchResult:
    filters = {
        key: value.strip()
        for key, value in (("name", name), ("department", department), ("job_title", job_title))
        if value and value.strip()
    }
    if not filters:
        raise InvalidRequestError(
            "Give at least one of: name, department, job_title",
            code="INVALID_SEARCH_CRITERIA",
        )
    payload = await gateway.call_tool(
        TOOL_SEARCH_EMPLOYEES,
        {**filters, "limit": limit, "offset": offset},
        user_id=user.user_id,
        user_scopes=user.scopes,
        required_scopes=[SCOPE_EMPLOYEES_READ],
    )
    return parse_result(EmployeeSearchResult, TOOL_SEARCH_EMPLOYEES, payload)
