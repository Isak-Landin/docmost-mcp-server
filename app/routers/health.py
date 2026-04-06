from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description="Returns `{ok: true}` when the service process is running and reachable. This does not verify live database connectivity.",
)
def health():
    return JSONResponse({"ok": True})
