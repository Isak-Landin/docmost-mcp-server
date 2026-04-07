# Overview

**Docmost MCP** is a read-only service that connects directly to a live Docmost PostgreSQL database and exposes that content through two surfaces:

- A **REST API** for conventional HTTP access
- A **remote MCP endpoint** for GitHub Copilot CLI and other MCP clients

## Purpose

The service bridges a running Docmost instance and AI tooling (Copilot CLI). It lets an AI assistant query documentation from Docmost without requiring write access or any modification to Docmost itself.

It is designed to run as a container on the same server and Docker network as the live Docmost stack, while being reachable from a separate machine running Copilot CLI.

## Key characteristics

- **Strictly read-only (via MCP)** — MCP tools expose no create, update, move, or delete operations
- **Write-capable via REST** — the service exposes write routes (`POST /spaces/{id}/pages`, etc.) that pass through to the Docmost REST API; requires Docmost **v0.71.1 or later** (see [Deployment](../Deployment/page.md))
- **Space-scoped** — pages are always queried within a space; there is no global page lookup
- **Normalized text** — `text_content` returned by the API has repeated newline runs and `+` storage noise collapsed before delivery
- **Explicit not-found errors** — if data does not exist the service returns a clear error; it never invents structure
- **Replica-aware** — exposes tools and routes to generate and manage a local documentation replica so AI clients can maintain a local editable copy of remote docs

## Tech stack

| Component | Technology |
|---|---|
| Web framework | FastAPI |
| MCP layer | `mcp` library (`FastMCP`) |
| Database | PostgreSQL via `psycopg2` |
| Models | Pydantic v2 |
| Runtime | Python 3.12 |
| Deployment | Docker / Docker Compose |

## Entry point

`app/main.py` — creates the FastAPI app, registers all routers, mounts the MCP sub-app, and manages the MCP session lifespan.
