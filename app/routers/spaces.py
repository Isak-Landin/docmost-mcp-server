from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import DocmostConnectionError
from app.docmost import SpaceNotFoundError, get_space as fetch_space, list_spaces as fetch_spaces
from app.models import SpaceOut

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get(
    "",
    response_model=List[SpaceOut],
    summary="List all spaces",
    description=(
        "Returns all non-deleted spaces from the live Docmost database, ordered by creation date. "
        "Use this first when you need to identify the correct space UUID before calling the page routes."
    ),
    responses={503: {"description": "Docmost database connection failed."}},
)
def list_spaces():
    try:
        return fetch_spaces()
    except DocmostConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get(
    "/{space_id}",
    response_model=SpaceOut,
    summary="Get a space",
    description=(
        "Returns a single space by its UUID. "
        "Returns 404 if the space does not exist or has been deleted."
    ),
    responses={
        404: {"description": "Space not found."},
        503: {"description": "Docmost database connection failed."},
    },
)
def get_space(space_id: UUID):
    try:
        return fetch_space(space_id)
    except DocmostConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SpaceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
