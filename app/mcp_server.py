from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from app.docmost import (
    PageNotFoundError,
    SpaceNotFoundError,
    get_page as fetch_page,
    get_space as fetch_space,
    list_pages as fetch_pages,
    list_spaces as fetch_spaces,
)
from app.models import PageOut, SpaceOut

SERVER_INSTRUCTIONS = """
This server is strictly read-only.
Never create, update, move, or delete spaces or pages.
Only use the provided Docmost tools to inspect spaces and pages.
Pages are always space-scoped: use space_id together with page_id.
Treat text_content as normalized plain text, not authoritative rich formatting.
If requested data is missing, report that explicitly instead of inferring it.
""".strip()

mcp = FastMCP(
    "Docmost Read-Only MCP",
    instructions=SERVER_INSTRUCTIONS,
    json_response=True,
)


@mcp.tool()
def list_spaces() -> list[SpaceOut]:
    """List all non-deleted Docmost spaces."""
    return fetch_spaces()


@mcp.tool()
def get_space(space_id: UUID) -> SpaceOut:
    """Get one Docmost space by UUID."""
    try:
        return fetch_space(space_id)
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def list_pages(space_id: UUID) -> list[PageOut]:
    """List all non-deleted pages in a Docmost space."""
    try:
        return fetch_pages(space_id)
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_page(space_id: UUID, page_id: UUID) -> PageOut:
    """Get one Docmost page by UUID within its space."""
    try:
        return fetch_page(space_id, page_id)
    except (PageNotFoundError, SpaceNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
