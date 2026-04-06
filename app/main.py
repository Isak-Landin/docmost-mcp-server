from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from app.mcp_server import mcp
from app.routers import health, spaces, pages


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="Docmost MCP",
    description="Read-only REST and MCP service for live Docmost PostgreSQL data. Exposes spaces and pages with normalized text content.",
    version="1.0.0",
    lifespan=app_lifespan,
)

app.include_router(health.router)
app.include_router(spaces.router)
app.include_router(pages.router)
# FastMCP already exposes its own /mcp route inside the sub-app.
app.mount("/", mcp.streamable_http_app())


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    port = int(os.getenv("LISTEN_PORT", "8099"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
