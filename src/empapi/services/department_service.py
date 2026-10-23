"""Department use cases."""

from __future__ import annotations

from empapi.deps import AuthenticatedUser
from empapi.exceptions import UpstreamError
from empapi.mcp.gateway import McpGateway
from empapi.mcp.consts import TOOL_DEPARTMENT_STATS
from empapi.models.department import DepartmentStatistics, DepartmentStatisticsResult
from empapi.security.scopes import SCOPE_DEPARTMENTS_READ
from empapi.services._parse import parse_result


async def _fetch(
    gateway: McpGateway,
    user: AuthenticatedUser,
    arguments: dict,
) -> DepartmentStatisticsResult:
    payload = await gateway.call_tool(
        TOOL_DEPARTMENT_STATS,
        arguments,
        user_id=user.user_id,
        user_scopes=user.scopes,
        required_scopes=[SCOPE_DEPARTMENTS_READ],
    )
    return parse_result(DepartmentStatisticsResult, TOOL_DEPARTMENT_STATS, payload)


async def all_departments(
    gateway: McpGateway, user: AuthenticatedUser, *, include_inactive: bool
) -> DepartmentStatisticsResult:
    return await _fetch(gateway, user, {"include_inactive": include_inactive})


async def department_by_id(
    gateway: McpGateway, user: AuthenticatedUser, department_id: int
) -> DepartmentStatistics:
    """A missing department is the MCP server's DEPARTMENT_NOT_FOUND, passed through as
    404. When an id is given the MCP server returns that department even if inactive."""
    result = await _fetch(gateway, user, {"department_id": department_id})
    if len(result.departments) != 1:
        raise UpstreamError(
            "The employee service returned an unexpected response",
            code="UPSTREAM_CONTRACT_ERROR",
        )
    return result.departments[0]
