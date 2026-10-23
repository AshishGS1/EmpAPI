"""/tools: what the MCP server offers, as discovered over the MCP protocol."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from empapi.deps import get_current_user, get_gateway
from empapi.mcp.gateway import McpGateway
from empapi.routers.responses import ERROR_RESPONSES
from empapi.models.common import ToolList, ToolSchema

router = APIRouter(
    prefix="/tools",
    tags=["tools"],
    dependencies=[Depends(get_current_user)],
    responses=ERROR_RESPONSES,
)


@router.get(
    "",
    response_model=ToolList,
    summary="List the MCP tools",
    description="Tools discovered with list_tools when the API connected to the MCP server "
    "(refreshed on every reconnect). Any authenticated user may read it.",
)
async def list_tools(gateway: McpGateway = Depends(get_gateway)) -> ToolList:
    tools = [ToolSchema(name=t.name, description=t.description, input_schema=t.input_schema)
             for t in gateway.tools]
    return ToolList(tools=tools, count=len(tools))
