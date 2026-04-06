from __future__ import annotations

import os
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.server import TransportSecuritySettings

from app.db import DocmostConnectionError
from app.docmost import (
    PageNotFoundError,
    SpaceNotFoundError,
    get_page as fetch_page,
    get_space as fetch_space,
    get_space_tree as fetch_space_tree,
    list_pages as fetch_pages,
    list_spaces as fetch_spaces,
)
from app.models import (
    PageOut,
    ReplicaNameResolutionOut,
    ReplicaStandardsOut,
    ReplicaStructureOut,
    SpaceOut,
    SpaceTreeOut,
)
from app.replica import (
    get_replica_standards as fetch_replica_standards,
    get_replica_structure as fetch_replica_structure,
    resolve_replica_directory_name as resolve_replica_directory_name_impl,
)

SERVER_INSTRUCTIONS = """
This server is strictly read-only.
Never create, update, move, or delete spaces or pages.
Use this server as the main documentation source for the active project when documentation is relevant.
Only use the provided Docmost tools to inspect spaces and pages.
Start with list_spaces when you need to identify the correct space.
If the user gives a space name rather than a UUID, find the matching space via list_spaces first.
When you need the page hierarchy of a space, prefer get_space_tree instead of reconstructing it yourself.
When you need the deterministic local replica layout for a space, use get_replica_structure.
When you need naming or sync rules for local replica work, use get_replica_standards.
When you need the correct local directory name for a planned page, use resolve_replica_directory_name.
Maintain or create a local replica at `./{space_name}-replica/` when the client workflow allows it, because the remote surface is read-only.
Use get_replica_structure as the source for the initial local replica layout and for refreshing existing remote-backed replica content.
Use get_replica_standards together with resolve_replica_directory_name for local-only documentation additions that do not yet exist on remote.
Use the returned space_id for list_pages and get_page.
Pages are always space-scoped: use space_id together with page_id, and use space_id for page listing.
Treat text_content as normalized plain text, not authoritative rich formatting.
If the user refers to docs, documented behavior, page names, or project guidance not fully present in the prompt, consult this server before guessing.
If newer local replica changes exist, treat the local replica as the working source of truth until a human syncs those changes back to remote Docmost.
When local replica files are edited, identify which local replica files changed, identify which remote page each file corresponds to when available, and tell the user to sync those local changes back to remote Docmost manually.
Use the replica tree mapping and page metadata to relate local files back to remote pages instead of guessing.
After local-only documentation edits, remote Docmost may be stale or effectively deprecated until manual sync occurs.
If content looks stale, deprecated, or inconsistent with newer verified behavior, say so explicitly.
If requested data is missing, report that explicitly instead of inferring it.
""".strip()

def _transport_security() -> TransportSecuritySettings:
    raw = os.getenv("MCP_ALLOWED_HOSTS", "")
    allowed = [h.strip() for h in raw.split(",") if h.strip()]
    return TransportSecuritySettings(allowed_hosts=allowed) if allowed else TransportSecuritySettings(
        enable_dns_rebinding_protection=False
    )


mcp = FastMCP(
    "Docmost MCP",
    instructions=SERVER_INSTRUCTIONS,
    json_response=True,
    transport_security=_transport_security(),
)


@mcp.tool()
def list_spaces() -> list[SpaceOut]:
    """List all non-deleted Docmost spaces. Use this first when you need to identify a space by name."""
    try:
        return fetch_spaces()
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_space(space_id: UUID) -> SpaceOut:
    """Get one Docmost space by UUID."""
    try:
        return fetch_space(space_id)
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_space_tree(space_id: UUID) -> SpaceTreeOut:
    """Get the fully nested page tree for one space identified by space_id."""
    try:
        return fetch_space_tree(space_id)
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_replica_standards() -> ReplicaStandardsOut:
    """Get the shared naming, layout, and sync rules for local documentation replicas."""
    return fetch_replica_standards()


@mcp.tool()
def resolve_replica_directory_name(
    title: str,
    slug_id: str | None = None,
    page_id: UUID | None = None,
    existing_dir_names: list[str] | None = None,
) -> ReplicaNameResolutionOut:
    """Resolve the correct local replica directory name for a page title under the shared standard."""
    return resolve_replica_directory_name_impl(
        title=title,
        slug_id=slug_id,
        page_id=page_id,
        existing_dir_names=existing_dir_names or [],
    )


@mcp.tool()
def get_replica_structure(space_id: UUID) -> ReplicaStructureOut:
    """Get the deterministic local replica layout for one space identified by space_id."""
    try:
        return fetch_replica_structure(space_id)
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def list_pages(space_id: UUID) -> list[PageOut]:
    """List all non-deleted pages in a Docmost space identified by space_id."""
    try:
        return fetch_pages(space_id)
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc
    except SpaceNotFoundError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def get_page(space_id: UUID, page_id: UUID) -> PageOut:
    """Get one Docmost page by UUID within its space. Use list_spaces and list_pages first if you only know names."""
    try:
        return fetch_page(space_id, page_id)
    except DocmostConnectionError as exc:
        raise ToolError(str(exc)) from exc
    except (PageNotFoundError, SpaceNotFoundError) as exc:
        raise ToolError(str(exc)) from exc
