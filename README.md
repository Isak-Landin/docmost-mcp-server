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
| REST API | `/health`, `/spaces`, `/spaces/{space_id}`, `/spaces/{space_id}/tree`, `/spaces/{space_id}/replica-structure`, `/spaces/{space_id}/pages`, `/spaces/{space_id}/pages/{page_id}`, `/replica/standards`, `/replica/resolve-directory-name` | Read-only HTTP access to spaces, trees, replica structure, replica standards, and pages |
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
| `GET` | `/health` | process health check only; does not verify database connectivity |
| `GET` | `/spaces` | list all non-deleted spaces |
| `GET` | `/spaces/{space_id}` | get one non-deleted space |
| `GET` | `/spaces/{space_id}/tree` | get the nested page tree for one space |
| `GET` | `/spaces/{space_id}/replica-structure` | get the deterministic local replica layout for one space |
| `GET` | `/spaces/{space_id}/pages` | list all non-deleted pages in a space |
| `GET` | `/spaces/{space_id}/pages/{page_id}` | get one non-deleted page in its space |
| `GET` | `/replica/standards` | get local replica naming, structure, and sync rules |
| `GET` | `/replica/resolve-directory-name` | resolve the correct local directory name for a page title under the shared standard |

## Exposed MCP tools

The MCP endpoint exposes these read-only tools:

| Tool | Description |
|---|---|
| `list_spaces` | list all non-deleted spaces |
| `get_space` | get one space by UUID |
| `get_space_tree` | get the nested page tree for one space |
| `get_replica_standards` | get local replica naming, structure, and sync rules |
| `resolve_replica_directory_name` | resolve the correct local directory name for a page title under the shared standard |
| `get_replica_structure` | get the deterministic local replica layout for one space |
| `list_pages` | list all pages in a space |
| `get_page` | get one page by UUID inside a space |

## Intended lookup flow

This service is intentionally **space-first**.

1. use `list_spaces` or `GET /spaces` to identify the correct Docmost space
2. select the matching space by name, then use its `id` as `space_id`
3. use `get_space_tree(space_id)` or `GET /spaces/{space_id}/tree` when you need the full nested structure quickly
4. use `list_pages(space_id)` or `GET /spaces/{space_id}/pages` when you need the flat list for inspection or follow-up lookups
5. use `get_page(space_id, page_id)` or `GET /spaces/{space_id}/pages/{page_id}` only after you know the correct IDs

Important clarifications:

- page lookup is not global; pages are always scoped to a space
- the tools and routes accept `space_id`, not a space name string
- if you only know a space name, resolve it through `list_spaces` first
- if content looks stale or deprecated, treat that as an explicit finding instead of silently assuming it is current
- the tree is built dynamically from `pages.parent_page_id`
- `parent_page_id = null` means the page is a top-level page in the space
- each tree node can contain arbitrarily deep nested `children`
- `orphan_pages` contains pages that could not be attached to a normal root because their parent is missing or otherwise unreachable

## Recommended documentation-source workflow

The intended usage is **not** merely "Docmost-related tasks."

The intended usage is:

- Docmost MCP is the main documentation source for the active project
- established project direction, user decisions, and documented behavior should be read from Docmost when they are not fully present in the prompt
- if the user refers to docs, documentation, a documented page, or a file/path that may be documented externally, check Docmost before guessing
- because the remote Docmost surface is currently read-only, Copilot should maintain a **local replica** of the retrieved documentation for copy-pasteable project truth and manual later sync

Recommended local-replica behavior:

1. create a local replica location if it does not already exist, at `./{space_name}-replica/`
2. use `get_replica_structure(space_id)` as the source for the initial replica layout of existing remote content
3. use `get_replica_standards()` and `resolve_replica_directory_name(...)` for new local-only documentation that does not yet exist on remote
4. update the local replica whenever newer remote Docmost content is established
5. apply requested documentation edits to the local replica, not to remote Docmost, while this service remains read-only
6. if local replica files have been edited, identify which local files changed, map them back to remote pages when possible, and tell the user those changes still need manual remote sync
7. treat the local replica as the working copy-pasteable documentation source until remote write support exists

Current limitation:

- the server is read-only, so this workflow depends on local-file maintenance by the client
- remote Docmost remains the source to read from, but the local replica is the place to keep immediately usable synced documentation text

## Replica structure and naming standard

Use the replica surfaces when you want the client to stop guessing local layout.

- use `get_replica_standards()` or `GET /replica/standards` for the shared policy
- use `get_replica_structure(space_id)` or `GET /spaces/{space_id}/replica-structure` for the full local layout of an existing remote space
- use `resolve_replica_directory_name(...)` or `GET /replica/resolve-directory-name` when creating a new local-only page directory that does not yet exist on remote

Replica root:

- root path: `./{space_name}-replica/`

Per-page replica mapping:

- every Docmost page maps to a **directory**
- the page's own content lives in `page.md`
- the page's metadata lives in `_meta.json`
- child pages become nested subdirectories under the parent page directory
- the replica tree output already maps each remote page to:
  - page `id`
  - page `title`
  - `content_file_path`
  - `meta_file_path`
- use that mapping plus each page directory's `_meta.json` to tell the user which local file corresponds to which remote page

Replica root support files:

- `_replica.json` stores replica-level metadata and sync state
- `_tree.json` stores the resolved tree snapshot used for the replica

Directory naming rule:

1. use the filesystem-safe page title as the base directory name
2. if sibling pages collide at the same level, use `{title}__{slug_id}`
3. if `slug_id` is missing or still collides, use `{title}__{short_page_id}`

Sync and truth rule:

- remote Docmost is the published read source
- the local replica is the editable working copy
- if newer local replica changes exist, the local replica becomes the working source of truth until a human syncs those changes back to remote
- after local-only edits, remote Docmost may be stale or effectively deprecated until that manual sync occurs
- when local replica files are edited, call out the changed local file paths explicitly
- when those edited files correspond to remote pages, identify the remote page title and page id explicitly
- prompt the user to copy those specific local changes back to remote Docmost

The MCP server also publishes built-in instructions:

```text
This server is strictly read-only.
Never create, update, move, or delete spaces or pages.
Use this server as the main documentation source for the active project when documentation is relevant.
Only use the provided Docmost tools to inspect spaces and pages.
Start with list_spaces when you need to identify the correct space.
If the user gives a space name rather than a UUID, find the matching space via list_spaces first.
When you need the page hierarchy of a space, use get_space_tree instead of reconstructing it manually.
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
| `app/replica.py` | replica naming, layout, and sync-rule logic |
| `app/routers/replica.py` | REST routes for replica standards, naming resolution, and replica structure |

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

This only confirms that the service process is reachable. It does **not** confirm that
the Docmost database is reachable.

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

To verify a database-backed route as part of manual testing, also try:

```bash
curl http://<YOUR_DOCMOST_MCP_HOST>:8099/spaces
```

If the database is unreachable, the read routes return:

- REST: `503` with `{"detail":"Docmost database connection failed"}`
- MCP: tool error with `Docmost database connection failed`

To inspect the exact local-replica projection for one space, use:

```text
http://<YOUR_DOCMOST_MCP_HOST>:8099/spaces/<SPACE_ID>/replica-structure
```

To inspect replica naming and sync rules without a space-specific lookup, use:

```text
http://<YOUR_DOCMOST_MCP_HOST>:8099/replica/standards
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

Configured MCP server details are saved per Copilot config home. The clean
Docmost-only setup is therefore to use a dedicated:

```text
COPILOT_HOME=~/.copilot-docmost
```

That keeps Docmost MCP configuration and Docmost-specific instructions out of your
normal default Copilot home.

### Recommended layout

Use these two files inside the dedicated Docmost home:

```text
~/.copilot-docmost/mcp-config.json
~/.copilot-docmost/copilot-instructions.md
```

Keep your normal:

```text
~/.copilot/copilot-instructions.md
```

generic. Do **not** keep Docmost-specific behavior in the default global
instructions file, or it will clash with unrelated work.

### Recommended start command

```bash
export COPILOT_HOME="$HOME/.copilot-docmost"
copilot
```

### Add the MCP server

Inside Copilot CLI:

```text
/mcp add
```

Then enter the remote HTTP MCP URL:

```text
https://<YOUR_DOCMOST_MCP_HOST>/mcp
```

Allow only these tools:

```text
list_spaces
get_space
get_space_tree
get_replica_standards
resolve_replica_directory_name
get_replica_structure
list_pages
get_page
```

After saving with `/mcp add`, verify that:

- the saved URL ends with `/mcp`
- there is no stray whitespace in the URL
- the allowlist includes the tree and replica tools, not just page lookup tools

### Recommended `mcp-config.json`

Store this in:

```text
$COPILOT_HOME/mcp-config.json
```

```json
{
  "mcpServers": {
    "docmost-mcp": {
      "type": "http",
      "url": "https://<YOUR_DOCMOST_MCP_HOST>/mcp",
      "tools": ["list_spaces", "get_space", "get_space_tree", "get_replica_standards", "resolve_replica_directory_name", "get_replica_structure", "list_pages", "get_page"]
    }
  }
}
```

### Recommended `copilot-instructions.md`

Store this in:

```text
$COPILOT_HOME/copilot-instructions.md
```

```md
# Instructions
Use the docmost-mcp MCP server as the main documentation source for the active project.
Treat it as read-only.
If documentation, documented behavior, page names, or relevant file/path references are mentioned without full context in the prompt, consult docmost-mcp before guessing.
Always resolve the correct space first, then inspect pages within that space.
Pages are space-scoped and are not global lookups.
Use get_space_tree when you need the nested structure of a space.
Maintain or create a local replica at `./{space_name}-replica/` when needed, because the remote Docmost surface is read-only.
Use get_replica_structure for the exact local replica layout of an existing space and for initial replica creation from remote content.
Use get_replica_standards and resolve_replica_directory_name for local-only additions that are not yet present on remote.
Use the replica tree mapping plus `_meta.json` to relate local replica files back to remote pages.
If newer local replica changes exist, treat the local replica as the working source of truth until the user syncs it back to remote.
If local replica files are edited, identify the changed local file paths, identify the corresponding remote pages when available, and tell the user those changes still need manual sync back to remote.
Treat remote Docmost as potentially stale after local-only edits until manual sync occurs.
If a page appears stale, deprecated, or older than verified current behavior, say that explicitly.
Prefer newer verified repo/runtime behavior over stale Docmost content when they conflict.
```

This is the one recommended Docmost-specific instruction file. Do not split the
same Docmost behavior across multiple competing instruction files unless you
deliberately want to manage instruction precedence yourself.

### Resulting behavior

With the dedicated Docmost home configured this way:

- Docmost MCP is available only when you start Copilot with `COPILOT_HOME="$HOME/.copilot-docmost"`
- the Docmost-specific instructions live alongside the Docmost MCP config
- your default global Copilot instructions stay free of Docmost-specific assumptions
- the consumer is explicitly told to:
  - use Docmost as the main documentation source
  - create and maintain `./{space_name}-replica/`
  - use `get_replica_structure` for initial replica creation and refresh
  - use `get_replica_standards` and `resolve_replica_directory_name` for local-only additions
  - map edited local replica files back to remote pages
  - prompt for manual remote sync when local replica content is newer than remote

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

### Page lookup is confusing or keeps failing

Check:

1. you identified the correct `space_id` via `/spaces` or `list_spaces` first
2. you are using that same `space_id` for `/spaces/{space_id}/tree`, `/spaces/{space_id}/pages`, `get_space_tree`, or `list_pages`
3. you are not treating page lookup as global across all spaces
4. the page may genuinely be stale, deleted, or in a different space

### Replica layout or naming is inconsistent

Check:

1. you are using `/spaces/{space_id}/replica-structure` or `get_replica_structure` for existing remote content
2. you are using `/replica/standards` or `get_replica_standards` for the shared local-replica rules
3. you are using `/replica/resolve-directory-name` or `resolve_replica_directory_name` for new local-only page directories
4. you are treating the local replica as the working source of truth only after newer local edits actually exist
5. you are treating remote Docmost as potentially stale after local-only documentation edits until manual sync occurs

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
If your `.env` uses a Docker-only hostname such as `db`, that local run will fail unless
your machine can resolve that hostname. For non-Docker local runs, set `DOCMOST_DB_HOST`
or `DOCMOST_DB_URL` to a database address reachable from the host machine.

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
