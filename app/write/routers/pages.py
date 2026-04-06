from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models import DeletedOut, PageCreateIn, PageOut, PageUpdateIn
from app.write.docmost import create_page as docmost_create_page
from app.write.docmost import delete_page as docmost_delete_page
from app.write.docmost import get_page_info
from app.write.docmost import update_page as docmost_update_page

router = APIRouter(prefix="/spaces/{space_id}/pages", tags=["pages"])


@router.post(
    "",
    response_model=PageOut,
    status_code=201,
    summary="Create a page",
    description=(
        "Creates a new page in the given space. "
        "Provide `parent_page_id` to create a child page nested under an existing page — "
        "arbitrarily deep hierarchies are supported. "
        "Content is accepted as **markdown** and converted server-side. "
        "The created page is returned with its full markdown content. "
        "Authentication is handled transparently."
    ),
    responses={
        400: {"description": "Validation error or Docmost rejected the request."},
        401: {"description": "Docmost credentials invalid."},
        404: {"description": "Space or parent page not found."},
    },
)
def create_page(space_id: UUID, body: PageCreateIn):
    try:
        data = docmost_create_page(
            space_id=str(space_id),
            title=body.title,
            content=body.content,
            parent_page_id=str(body.parent_page_id) if body.parent_page_id else None,
        )
    except Exception as exc:
        _raise_for_docmost_error(exc)

    page_id = data.get("id") or (data.get("page", {}) or {}).get("id")
    if not page_id:
        raise HTTPException(status_code=502, detail=f"Docmost create did not return a page id. Response: {data}")

    try:
        full = get_page_info(page_id)
    except Exception:
        full = data

    return _map_page(full)


@router.put(
    "/{page_id}",
    response_model=PageOut,
    summary="Update a page",
    description=(
        "Updates an existing page's title and/or content. "
        "Content is accepted as **markdown**. "
        "Use `operation='replace'` (default) to overwrite, `'append'` to add after existing "
        "content, or `'prepend'` to add before. "
        "Prefer update over delete+create — Docmost preserves page history on update. "
        "Authentication is handled transparently."
    ),
    responses={
        400: {"description": "Validation error or Docmost rejected the request."},
        401: {"description": "Docmost credentials invalid."},
        404: {"description": "Page not found."},
    },
)
def update_page(space_id: UUID, page_id: UUID, body: PageUpdateIn):
    try:
        docmost_update_page(
            page_id=str(page_id),
            title=body.title,
            content=body.content,
            operation=body.operation,
        )
    except Exception as exc:
        _raise_for_docmost_error(exc)

    try:
        full = get_page_info(str(page_id))
    except Exception as exc:
        _raise_for_docmost_error(exc)

    return _map_page(full)


@router.delete(
    "/{page_id}",
    response_model=DeletedOut,
    summary="Delete a page",
    description=(
        "Soft-deletes a page (moves to trash in Docmost). "
        "Authentication is handled transparently."
    ),
    responses={
        401: {"description": "Docmost credentials invalid."},
        404: {"description": "Page not found."},
    },
)
def delete_page(space_id: UUID, page_id: UUID):
    try:
        docmost_delete_page(str(page_id))
    except Exception as exc:
        _raise_for_docmost_error(exc)
    return DeletedOut(deleted=True, id=str(page_id))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_for_docmost_error(exc: Exception) -> None:
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text
        raise HTTPException(status_code=status, detail=detail) from exc
    raise HTTPException(status_code=502, detail=str(exc)) from exc


def _map_page(data: dict) -> PageOut:
    """Map a Docmost page response dict to PageOut, converting content to markdown."""
    from datetime import datetime
    from app.query.prosemirror import prosemirror_to_markdown

    page = data.get("page", data)

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
        space_id=page.get("spaceId") or page.get("space_id"),
        workspace_id=page.get("workspaceId") or page.get("workspace_id"),
        is_locked=page.get("isLocked") or page.get("is_locked") or False,
        content=content,
        created_at=page.get("createdAt") or page.get("created_at") or datetime.utcnow(),
        updated_at=page.get("updatedAt") or page.get("updated_at") or datetime.utcnow(),
    )
