import random
import string
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import get_conn
from app.models import PageOut, PageCreate, PageUpdate
from app.text_utils import reformat_text

router = APIRouter(prefix="/spaces/{space_id}/pages", tags=["pages"])


def _gen_slug(length: int = 10) -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def _assert_space_exists(cur, space_id: UUID) -> dict:
    cur.execute(
        "SELECT id, workspace_id FROM public.spaces WHERE id = %s AND deleted_at IS NULL LIMIT 1",
        (str(space_id),),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Space not found")
    return dict(row)


def _assert_page_in_space(cur, page_id: UUID, space_id: UUID) -> dict:
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
        raise HTTPException(status_code=404, detail="Page not found in this space")
    return dict(row)


def _format_page(row: dict) -> dict:
    row = dict(row)
    if row.get("text_content"):
        row["text_content"] = reformat_text(row["text_content"])
    return row


@router.get(
    "",
    response_model=List[PageOut],
    summary="List pages in a space",
    description=(
        "Returns all non-deleted pages belonging to the given space, ordered by creation date. "
        "`text_content` is returned normalized: repeated newline runs and repeated `+` storage "
        "noise are collapsed."
    ),
)
def list_pages(space_id: UUID):
    sql = """
        SELECT id, slug_id, title, icon, position, parent_page_id, creator_id,
               last_updated_by_id, space_id, workspace_id, is_locked,
               text_content, created_at, updated_at
        FROM public.pages
        WHERE space_id = %s AND deleted_at IS NULL
        ORDER BY created_at ASC
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            cur.execute(sql, (str(space_id),))
            rows = cur.fetchall()
    return [_format_page(r) for r in rows]


@router.post(
    "",
    response_model=PageOut,
    status_code=201,
    summary="Create a page",
    description=(
        "Creates a new page inside the given space. "
        "`title` is required. `parent_page_id` must belong to the same space if provided. "
        "`text_content` is stored as plain text."
    ),
)
def create_page(space_id: UUID, body: PageCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            space = _assert_space_exists(cur, space_id)
            workspace_id = space["workspace_id"]

            if body.parent_page_id:
                _assert_page_in_space(cur, body.parent_page_id, space_id)

            slug_id = _gen_slug()
            sql = """
                INSERT INTO public.pages
                    (slug_id, title, parent_page_id, space_id, workspace_id,
                     is_locked, text_content, created_at, updated_at)
                VALUES
                    (%s, %s, %s, %s, %s, false, %s, now(), now())
                RETURNING id, slug_id, title, icon, position, parent_page_id,
                          creator_id, last_updated_by_id, space_id, workspace_id,
                          is_locked, text_content, created_at, updated_at
            """
            cur.execute(
                sql,
                (
                    slug_id,
                    body.title,
                    str(body.parent_page_id) if body.parent_page_id else None,
                    str(space_id),
                    str(workspace_id),
                    body.text_content,
                ),
            )
            row = cur.fetchone()
    return _format_page(row)


@router.get(
    "/{page_id}",
    response_model=PageOut,
    summary="Get a page",
    description=(
        "Returns a single page by its UUID, scoped to the given space. "
        "Returns 404 if the page does not exist, is deleted, or belongs to a different space."
    ),
)
def get_page(space_id: UUID, page_id: UUID):
    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            row = _assert_page_in_space(cur, page_id, space_id)
    return _format_page(row)


@router.patch(
    "/{page_id}",
    response_model=PageOut,
    summary="Update a page",
    description=(
        "Partially updates a page. Accepted fields: `title`, `parent_page_id`, `text_content`. "
        "At least one field must be provided. `parent_page_id` must belong to the same space if provided."
    ),
)
def update_page(space_id: UUID, page_id: UUID, body: PageUpdate):
    if not any([body.title is not None, body.parent_page_id is not None, body.text_content is not None]):
        raise HTTPException(status_code=400, detail="No fields provided for update")

    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            _assert_page_in_space(cur, page_id, space_id)

            if body.parent_page_id:
                _assert_page_in_space(cur, body.parent_page_id, space_id)

            updates = []
            params = []
            if body.title is not None:
                updates.append("title = %s")
                params.append(body.title)
            if body.parent_page_id is not None:
                updates.append("parent_page_id = %s")
                params.append(str(body.parent_page_id))
            if body.text_content is not None:
                updates.append("text_content = %s")
                params.append(body.text_content)
            updates.append("updated_at = now()")

            params.extend([str(page_id), str(space_id)])
            sql = f"""
                UPDATE public.pages
                SET {", ".join(updates)}
                WHERE id = %s AND space_id = %s AND deleted_at IS NULL
                RETURNING id, slug_id, title, icon, position, parent_page_id,
                          creator_id, last_updated_by_id, space_id, workspace_id,
                          is_locked, text_content, created_at, updated_at
            """
            cur.execute(sql, params)
            row = cur.fetchone()
    return _format_page(row)


@router.delete(
    "/{page_id}",
    status_code=204,
    summary="Delete a page",
    description=(
        "Soft-deletes a page by setting `deleted_at`. The row is not removed from the database. "
        "Returns 404 if the page does not exist or belongs to a different space."
    ),
)
def delete_page(space_id: UUID, page_id: UUID):
    with get_conn() as conn:
        with conn.cursor() as cur:
            _assert_space_exists(cur, space_id)
            _assert_page_in_space(cur, page_id, space_id)
            cur.execute(
                """
                UPDATE public.pages
                SET deleted_at = now()
                WHERE id = %s AND space_id = %s AND deleted_at IS NULL
                """,
                (str(page_id), str(space_id)),
            )
