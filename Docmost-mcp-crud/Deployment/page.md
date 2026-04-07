# Deployment

## Overview

The service is deployed as a Docker container on the same server as the live Docmost stack, joined to the same Docker network so it can reach the Docmost PostgreSQL container.

## Docmost version requirement

**Docmost v0.71.1 or later is required for content write operations to work.**

In older versions, `CreatePageDto` and `UpdatePageDto` did not declare `content` or `format`. NestJS `ValidationPipe({ whitelist: true })` strips undeclared fields silently, so page content was always discarded. From v0.71.1 both fields are fully declared and supported.

To check the version running on your Docmost host:

```bash
docker exec docmost cat /app/apps/server/package.json | grep '"version"' | head -1
```

To update Docmost safely (no volume loss):

```bash
docker compose pull docmost
docker compose up -d --no-deps docmost
```

## Docker Compose

`docker-compose.yml` defines one service: `docmost-mcp`.

Key configuration:
- Reads env from `.env` via `env_file`
- Sets DB and server env vars explicitly from `.env` values
- Publishes `EXTERNAL_PORT` (default 8099) → `LISTEN_PORT` (default 8099)
- Joins the `docmost_network` Docker network (external, expected to already exist as `docmost_default`)

## Network requirement

The `docmost_network` must already exist as an external Docker network named `docmost_default`. This is the network created by the live Docmost Docker Compose stack.

If your Docmost network has a different name, update the `networks.docmost_network.name` value in `docker-compose.yml`.

## Setup steps

Two setup methods are available:

**Option A - from the published Docker image (recommended):**

1. Create a directory on the server running Docmost
2. Create a `docker-compose.yml` pointing at `ghcr.io/isak-landin/docmost-mcp-api:latest` (see README for full example)
3. Copy `env.example` to `.env` and fill in values
4. Ensure the `docmost_default` Docker network exists
5. Run:
   ```bash
   docker compose up -d
   ```

**Option B - from source:**

1. Clone this repository onto the server running Docmost
2. Copy `env.example` to `.env` and fill in values (DB credentials, allowed MCP hosts)
3. Ensure the `docmost_default` Docker network exists
4. Run:
   ```bash
   docker compose up -d --build
   ```

Verify with:
```bash
curl http://localhost:8099/health
# → {"ok": true}
```

## Dockerfile

The Dockerfile installs Python dependencies from `requirements.txt` and runs:
```
python -m app.main
```

## Copilot CLI integration

On the remote machine (where Copilot CLI runs), add the MCP server in your Copilot CLI settings pointing to:
```
https://<YOUR_HOST>:<EXTERNAL_PORT>/mcp
```

If using a reverse proxy with a custom domain, set `MCP_ALLOWED_HOSTS` in `.env` to that domain.

## Runtime defaults

| Setting | Default |
|---|---|
| Listen host | `0.0.0.0` |
| Listen port | `8099` |
| External port | `8099` |
