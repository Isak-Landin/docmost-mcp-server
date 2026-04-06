# Docmost MCP

Docmost MCP is a read-only service that connects directly to a live Docmost PostgreSQL
database and exposes that content through:

- a REST API for conventional HTTP access
- a remote MCP endpoint for GitHub Copilot CLI and other MCP clients

It is designed to run as a container on the same server and Docker network as the
live Docmost stack, while being reachable from a separate machine running Copilot CLI.

## What this project does

This service exposes:

| Surface | Path | Purpose |
|---|---|---|
| REST API | `/health`, `/spaces`, `/spaces/{space_id}`, `/spaces/{space_id}/pages`, `/spaces/{space_id}/pages/{page_id}` | Read-only HTTP access to spaces and pages |
| MCP | `/mcp` | Remote streamable HTTP MCP endpoint |

This service does **not** expose write operations.

## Read-only contract

- no create, update, move, or delete operations
- pages are always scoped to a space
- page text is returned as normalized plain text
- repeated newline runs and repeated `+` storage noise are collapsed
- if data does not exist, the service returns explicit not found errors instead of inventing structure

## Exposed REST routes

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | health check |
| `GET` | `/spaces` | list all non-deleted spaces |
| `GET` | `/spaces/{space_id}` | get one non-deleted space |
| `GET` | `/spaces/{space_id}/pages` | list all non-deleted pages in a space |
| `GET` | `/spaces/{space_id}/pages/{page_id}` | get one non-deleted page in its space |

## Exposed MCP tools

The MCP endpoint exposes these read-only tools:

| Tool | Description |
|---|---|
| `list_spaces` | list all non-deleted spaces |
| `get_space` | get one space by UUID |
| `list_pages` | list all pages in a space |
| `get_page` | get one page by UUID inside a space |

The MCP server also publishes built-in instructions:

```text
This server is strictly read-only.
Never create, update, move, or delete spaces or pages.
Only use the provided Docmost tools to inspect spaces and pages.
Pages are always space-scoped: use space_id together with page_id.
Treat text_content as normalized plain text, not authoritative rich formatting.
If requested data is missing, report that explicitly instead of inferring it.
```

## Architecture

Typical deployment:

1. the live Docmost stack already exists on a server
2. this service runs as a separate container on that same server
3. this service joins the same Docker network as Docmost so it can reach the Docmost PostgreSQL container
4. Copilot CLI runs on a different machine and connects remotely to `https://<YOUR_DOCMOST_MCP_HOST>/mcp`

## Prerequisites

Before setup, make sure you have:

1. a running Docmost environment with PostgreSQL
2. Docker and Docker Compose available on the server where this service will run
3. network access from this service container to the live Docmost PostgreSQL container
4. network access from your Copilot CLI machine to the published Docmost MCP URL
5. the Docmost database credentials or DSN

## Files in this project

Important files:

| File | Purpose |
|---|---|
| `Dockerfile` | builds the Docmost MCP image |
| `docker-compose.yml` | runs the Docmost MCP container |
| `env.example` | example runtime configuration |
| `requirements.txt` | Python dependencies |
| `app/main.py` | FastAPI application entrypoint |
| `app/mcp_server.py` | MCP server definition |

## Full setup from start to finish

### 1. Copy the project to the target server

Put the repository on the same server that hosts the live Docmost deployment.

Example placeholder path:

```bash
mkdir -p /opt/docmost-mcp
cd /opt/docmost-mcp
```

Place the project files there.

### 2. Confirm the shared Docker network name

This project expects the external Docker network:

```text
docmost_default
```

That is the network currently referenced in `docker-compose.yml`.

If your live Docmost stack uses a different Docker network name, update this block:

```yaml
networks:
  docmost_network:
    external: true
    name: docmost_default
```

### 3. Create the runtime environment file

Copy the example file:

```bash
cp env.example .env
```

Then edit `.env`.

### 4. Fill in `.env`

You can configure the database in one of two ways.

#### Option A: full DSN

Use `DOCMOST_DB_URL` if you want a single connection string:

```env
DOCMOST_DB_URL=postgresql://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:5432/<DB_NAME>
```

#### Option B: separate values

If you do not use `DOCMOST_DB_URL`, set the individual values:

```env
DOCMOST_DB_HOST=<DOCMOST_DB_HOSTNAME_ON_DOCKER_NETWORK>
DOCMOST_DB_PORT=5432
DOCMOST_DB_NAME=<DOCMOST_DB_NAME>
DOCMOST_DB_USER=<DOCMOST_DB_USER>
DOCMOST_DB_PASSWORD=<DOCMOST_DB_PASSWORD>
```

#### API and MCP listen values

These control where the container listens:

```env
LISTEN_HOST=0.0.0.0
LISTEN_PORT=8099
EXTERNAL_PORT=8099
```

Meaning:

- `LISTEN_HOST`: bind host inside the container
- `LISTEN_PORT`: port inside the container
- `EXTERNAL_PORT`: port published on the server

#### Example full `.env`

```env
DOCMOST_DB_URL=
DOCMOST_DB_HOST=<DOCMOST_DB_HOSTNAME_ON_DOCKER_NETWORK>
DOCMOST_DB_PORT=5432
DOCMOST_DB_NAME=<DOCMOST_DB_NAME>
DOCMOST_DB_USER=<DOCMOST_DB_USER>
DOCMOST_DB_PASSWORD=<DOCMOST_DB_PASSWORD>

LISTEN_HOST=0.0.0.0
LISTEN_PORT=8099
EXTERNAL_PORT=8099

MODE=prod
LOG_LEVEL=INFO
```

### 5. Build and start the container

From the project directory:

```bash
docker compose up --build -d
```

This will:

1. build the image from `Dockerfile`
2. create or recreate the `docmost-mcp` container
3. attach it to the external `docmost_default` network
4. expose the service on the configured external port

### 6. Confirm the container is running

```bash
docker compose ps
```

You should see the `docmost-mcp` service/container running.

If you need logs:

```bash
docker compose logs -f
```

### 7. Verify the HTTP endpoints

Use placeholders for your real host name or IP:

```bash
curl http://<YOUR_DOCMOST_MCP_HOST>:8099/health
```

Expected response:

```json
{"ok":true}
```

Open the REST docs:

```text
http://<YOUR_DOCMOST_MCP_HOST>:8099/docs
```

MCP endpoint:

```text
http://<YOUR_DOCMOST_MCP_HOST>:8099/mcp
```

If you are putting this behind a reverse proxy, the MCP URL may instead be:

```text
https://<YOUR_DOCMOST_MCP_HOST>/mcp
```

### 8. Optional: place behind HTTPS or a reverse proxy

If Copilot CLI runs on another machine, HTTPS is usually the cleanest approach.

Typical reverse proxy responsibilities:

- terminate TLS
- expose a stable hostname
- forward `/mcp` to the container
- forward `/health`, `/docs`, and REST routes if you want those externally reachable

Example placeholder public URL:

```text
https://<YOUR_DOCMOST_MCP_HOST>/mcp
```

## GitHub Copilot CLI setup

Because the MCP endpoint is remote and container-hosted, your GitHub Copilot CLI
machine does **not** need any local wrapper script for Docmost MCP.

Copilot CLI only needs a configured MCP server pointing at the remote URL.

Copilot CLI already includes the GitHub MCP server by default. Docmost MCP is an
additional remote MCP server you add to extend Copilot CLI with Docmost read access.

## Important MCP scope behavior in Copilot CLI

GitHub's Copilot CLI documentation states that configured MCP server details are
stored by default in:

```text
~/.copilot/mcp-config.json
```

That default location can be changed with:

```text
COPILOT_HOME
```

That means:

- adding an MCP server is not a one-time per-session action
- MCP server configuration persists across sessions for that Copilot config home
- if you use your normal default Copilot config, the MCP server may be available in unrelated projects too

## Recommended safe setup for Docmost-only use

Use a separate Copilot config home for Docmost work.

### 1. Create a dedicated Copilot home

Example:

```bash
export COPILOT_HOME="$HOME/.copilot-docmost"
copilot
```

That creates an isolated Copilot configuration set for Docmost work.

### 2. Add the remote MCP server inside that Docmost-only Copilot environment

Inside Copilot CLI:

```text
/mcp add
```

Then:

1. enter the remote MCP server details
2. use <kbd>Tab</kbd> to move between fields
3. press <kbd>Ctrl</kbd>+<kbd>S</kbd> to save

Use a remote HTTP MCP server with a placeholder URL like:

```text
https://<YOUR_DOCMOST_MCP_HOST>/mcp
```

Allow only these tools:

```text
list_spaces
get_space
list_pages
get_page
```

### 3. Use that isolated Copilot environment only for Docmost-related sessions

When you want Docmost MCP available:

```bash
export COPILOT_HOME="$HOME/.copilot-docmost"
copilot
```

When you do **not** want Docmost MCP available:

```bash
unset COPILOT_HOME
copilot
```

or set `COPILOT_HOME` to some other non-Docmost config directory.

This is the cleanest way to avoid exposing Docmost MCP in unrelated projects.

## Manual Copilot CLI MCP configuration

If you prefer to edit the config manually, create or update:

```text
~/.copilot/mcp-config.json
```

Example:

```json
{
  "mcpServers": {
    "docmost-mcp": {
      "type": "http",
      "url": "https://<YOUR_DOCMOST_MCP_HOST>/mcp",
      "tools": ["list_spaces", "get_space", "list_pages", "get_page"]
    }
  }
}
```

This JSON structure matches the documented `mcpServers` format for Copilot MCP
configuration: the server name maps to an object with `type`, `url`, and an explicit
`tools` allowlist.

If you are using the isolated configuration approach, this file lives under that
Copilot home instead, for example:

```text
$COPILOT_HOME/mcp-config.json
```

## Per-session guidance for Copilot CLI

Even when the MCP server is already configured, it is still useful to guide the model
inside a given session.

At the beginning of a Docmost-related Copilot session, tell Copilot something like:

```text
Use the docmost-mcp server for Docmost content lookup in this session.
Treat it as read-only.
Do not use it for unrelated repositories or unrelated tasks.
```

This is not a replacement for isolated config, but it improves behavior within the session.

## Optional Copilot CLI instructions for Docmost repositories

If you work in one or more repositories that are specifically tied to Docmost content,
you can also add Copilot instructions such as:

```md
Use the docmost-mcp MCP server only for Docmost-related tasks in this repository.
Treat the server as read-only.
Do not use the Docmost MCP server in unrelated repositories.
```

For GitHub Copilot CLI, repository-wide instructions can live in:

```text
.github/copilot-instructions.md
```

Copilot CLI also supports path-specific instruction files in:

```text
.github/instructions/**/*.instructions.md
```

and user-level instructions in:

```text
$HOME/.copilot/copilot-instructions.md
```

## Updating the running service

When you change code or dependencies:

```bash
docker compose up --build -d
```

To restart without rebuilding:

```bash
docker compose restart
```

To stop the service:

```bash
docker compose down
```

## Troubleshooting

### Health endpoint fails

Check:

1. the container is running
2. the published port is correct
3. the reverse proxy is forwarding correctly if one is used

### MCP cannot connect

Check:

1. the configured MCP URL ends with `/mcp`
2. the Copilot CLI machine can reach the host and port
3. HTTPS or proxy settings are correct if the endpoint is remote
4. the MCP config only includes the intended read-only tools

### Database connection fails

Check:

1. the credentials in `.env`
2. the database host name reachable from inside the Docker network
3. the external network name in `docker-compose.yml`
4. whether the live Docmost PostgreSQL container is actually on that network

### Wrong scope in Copilot CLI

If Docmost MCP is appearing in unrelated work:

1. move it into a dedicated `COPILOT_HOME`
2. remove it from your default `~/.copilot/mcp-config.json`
3. start Docmost-only sessions with the dedicated Copilot home

## Local non-Docker run

If you want to run the service locally without Docker:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8099
```

You still need valid Docmost database connectivity through the configured env vars.

## Data model

**Spaces** - `public.spaces`

Columns exposed: `id`, `name`, `description`, `slug`, `visibility`, `default_role`,
`creator_id`, `workspace_id`, `created_at`, `updated_at`.

**Pages** - `public.pages`

Columns exposed: `id`, `slug_id`, `title`, `icon`, `position`, `parent_page_id`,
`creator_id`, `last_updated_by_id`, `space_id`, `workspace_id`, `is_locked`,
`text_content`, `created_at`, `updated_at`.

Deleted Docmost rows are excluded by checking `deleted_at IS NULL`.

## License

See `LICENSE`.
