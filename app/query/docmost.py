from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any
from uuid import UUID

from app.query.db import get_conn
from app.models import PageOut, PageTreeNode, SpaceOut, SpaceSummaryOut, SpaceTreeOut
from app.query.text_utils import reformat_text


class SpaceNotFoundError(Exception):
    pass


class PageNotFoundError(Exception):
    pass


def _assert_space_exists(cur, space_id: UUID) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, name, description, slug, visibility, default_role,
               creator_id, workspace_id, created_at, updated_at
        FROM public.spaces
        WHERE id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (str(space_id),),
    )
    row = cur.fetchone()
    if not row:
        raise SpaceNotFoundError("Space not found")
    return dict(row)


def _assert_page_in_space(cur, page_id: UUID, space_id: UUID) -> dict[str, Any]:
    cur.execute(
        """
        SELECT id, slug_id, title, icon, position, parent_page_id, creator_id,
               last_updated_by_id, space_id, workspace_id, is_locked,
               text_content, created_at, updated_at
        FROM public.pages
        WHERE id = %s AND space_id = %s AND deleted_at IS NULL
        LIMIT 1
        """,
        (str(page_id), str(space_id)),
    )
    row = cur.fetchone()
    if not row:
        raise PageNotFoundError("Page not found in this space")
    return dict(row)


def _format_page(row: dict[str, Any]) -> PageOut:
    """Map a DB row to PageOut without content (content is fetched via REST)."""
    return PageOut(
        id=row["id"],
        slug_id=row["slug_id"],
        title=row.get("title"),
        icon=row.get("icon"),
        position=row.get("position"),
        parent_page_id=row.get("parent_page_id"),
        creator_id=row.get("creator_id"),
        last_updated_by_id=row.get("last_updated_by_id"),
        space_id=row["space_id"],
        workspace_id=row["workspace_id"],
        is_locked=row.get("is_locked", False),
        content=None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _page_row_sort_key(row: dict[str, Any]) -> tuple[int, str, datetime]:
    position = row.get("position")
    created_at = row.get("created_at") or datetime.min
    return (0 if position is not None else 1, str(position or ""), created_at)


def _fetch_space_page_rows(cur, space_id: UUID) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, slug_id, title, icon, position, parent_page_id, created_at
        FROM public.pages
        WHERE space_id = %s AND deleted_at IS NULL
        ORDER BY created_at ASC
        """,
        (str(space_id),),
    )
    return [dict(row) for row in cur.fetchall()]


def _build_tree_node(
    page_row: dict[str, Any],
    child_rows_by_parent: dict[UUID, list[dict[str, Any]]],
    attached_page_ids: set[UUID],
    current_path: set[UUID],
) -> PageTreeNode:
    page_id = page_row["id"]
    attached_page_ids.add(page_id)
    next_path = set(current_path)
    next_path.add(page_id)

    child_nodes: list[PageTreeNode] = []
    for child_row in child_rows_by_parent.get(page_id, []):
        child_id = child_row["id"]
        if child_id in next_path:
            continue
        child_nodes.append(_build_tree_node(child_row, child_rows_by_parent, attached_page_ids, next_path))

    return PageTreeNode(
        id=page_id,
        title=page_row.get("title"),
        slug_id=page_row["slug_id"],
        icon=page_row.get("icon"),
        parent_page_id=page_row.get("parent_page_id"),
        position=page_row.get("position"),
        has_children=bool(child_rows_by_parent.get(page_id)),
        children=child_nodes,
    )


def list_spaces() -> list[SpaceOut]:
    sql = """
        SELECT id, name, description, slug, visibility, default_role,
               creator_id, workspace_id, created_at, updated_at
        FROM public.spaces
        WHERE deleted_at IS NULL
        ORDER BY created_at ASC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    return [SpaceOut(**dict(row)) for row in rows]


def get_space(space_id: UUID) -> SpaceOut:
    with get_conn() as conn:
        with conn.cursor() as cur:
            return SpaceOut(**_assert_space_exists(cur, space_id))


def list_pages(space_id: UUID) -> list[PageOut]:
    sql = """
        SELECT id, slug_id, title, icon, position, parent_page_id, creator_id,
               last_updated_by_id, space_id, workspace_id, is_locked,
               created_at, updated_at
        FROM public.pages
        WHERE space_id = %s AND deleted_at IS NULL
        ORDER BY created_at ASC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            cur.execute(sql, (str(space_id),))
            rows = cur.fetchall()
    return [_format_page(dict(row)) for row in rows]


def get_page(space_id: UUID, page_id: UUID) -> PageOut:
    """Return a page with its content as markdown, fetched via Docmost REST."""
    from app.write.docmost import get_page_info
    from app.query.prosemirror import prosemirror_to_markdown

    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            _assert_page_in_space(cur, page_id, space_id)

    data = get_page_info(str(page_id))
    page = data.get("page", data)

    from datetime import datetime as _dt

    raw_content = page.get("content")
    if isinstance(raw_content, dict):
        content = prosemirror_to_markdown(raw_content)
    else:
        content = raw_content

    return PageOut(
        id=page["id"],
        slug_id=page.get("slugId") or page.get("slug_id") or "",
        title=page.get("title"),
        icon=page.get("icon"),
        position=page.get("position"),
        parent_page_id=page.get("parentPageId") or page.get("parent_page_id"),
        creator_id=page.get("creatorId") or page.get("creator_id"),
        last_updated_by_id=page.get("lastUpdatedById") or page.get("last_updated_by_id"),
        space_id=page.get("spaceId") or page.get("space_id") or str(space_id),
        workspace_id=page.get("workspaceId") or page.get("workspace_id") or "",
        is_locked=page.get("isLocked") or page.get("is_locked") or False,
        content=content,
        created_at=page.get("createdAt") or page.get("created_at") or _dt.utcnow(),
        updated_at=page.get("updatedAt") or page.get("updated_at") or _dt.utcnow(),
    )


def get_space_tree(space_id: UUID) -> SpaceTreeOut:
    with get_conn() as conn:
        with conn.cursor() as cur:
            space_row = _assert_space_exists(cur, space_id)
            page_rows = _fetch_space_page_rows(cur, space_id)

    rows_by_id = {row["id"]: row for row in page_rows}
    child_rows_by_parent: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    root_rows: list[dict[str, Any]] = []
    orphan_root_rows: list[dict[str, Any]] = []

    for row in page_rows:
        parent_page_id = row.get("parent_page_id")
        if parent_page_id is None:
            root_rows.append(row)
        elif parent_page_id not in rows_by_id:
            orphan_root_rows.append(row)
        else:
            child_rows_by_parent[parent_page_id].append(row)

    root_rows.sort(key=_page_row_sort_key)
    orphan_root_rows.sort(key=_page_row_sort_key)
    for child_rows in child_rows_by_parent.values():
        child_rows.sort(key=_page_row_sort_key)

    attached_page_ids: set[UUID] = set()
    root_pages = [
        _build_tree_node(row, child_rows_by_parent, attached_page_ids, set())
        for row in root_rows
    ]

    orphan_pages = [
        _build_tree_node(row, child_rows_by_parent, attached_page_ids, set())
        for row in orphan_root_rows
        if row["id"] not in attached_page_ids
    ]

    remaining_rows = sorted(
        (row for row in page_rows if row["id"] not in attached_page_ids),
        key=_page_row_sort_key,
    )
    orphan_pages.extend(
        _build_tree_node(row, child_rows_by_parent, attached_page_ids, set())
        for row in remaining_rows
        if row["id"] not in attached_page_ids
    )

    return SpaceTreeOut(
        space=SpaceSummaryOut(
            id=space_row["id"],
            name=space_row.get("name"),
            slug=space_row["slug"],
        ),
        root_pages=root_pages,
        orphan_pages=orphan_pages,
    )
