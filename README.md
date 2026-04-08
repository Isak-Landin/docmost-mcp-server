# Docmost MCP

Docmost MCP runs alongside a live Docmost deployment on the same Docker network,
connects directly to the Docmost PostgreSQL database, and exposes that content
through both a remote MCP endpoint for agents and a REST API for conventional
HTTP integrations.

It is designed for the common setup where Docmost stays containerized on one
server while GitHub Copilot CLI or another MCP-compatible client connects from a
different machine.

## MCP capabilities

The `/mcp` endpoint gives GitHub Copilot CLI and other MCP-compatible clients a
remote Docmost toolset over streamable HTTP.

| Capability | Tools |
|---|---|
| Resolve the correct Docmost space | `list_spaces`, `get_space` |
| Inspect hierarchy and page listings | `get_space_tree`, `list_pages` |
| Read full page content as markdown | `get_page` |
| Inspect replica rules and layout | `get_replica_standards`, `resolve_replica_directory_name`, `get_replica_structure` |
| Create or delete spaces | `create_space`, `delete_space` |
| Create, update, or delete pages | `create_page`, `update_page`, `delete_page` |

All page content is markdown in and markdown out.

## REST capabilities

The REST API exposes the same core access patterns over HTTP for direct
integrations, manual inspection, and non-MCP automation.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | process health check only; does not verify database connectivity |
| `GET` | `/spaces` | list all non-deleted spaces |
| `GET` | `/spaces/{space_id}` | get one non-deleted space |
| `GET` | `/spaces/{space_id}/tree` | get the nested page tree for one space |
| `GET` | `/spaces/{space_id}/replica-structure` | get the deterministic local replica layout for one space |
| `GET` | `/spaces/{space_id}/pages` | list all non-deleted pages in a space (no content) |
| `GET` | `/spaces/{space_id}/pages/{page_id}` | get one page with full markdown content |
| `GET` | `/replica/standards` | get local replica naming, structure, and sync rules |
| `GET` | `/replica/resolve-directory-name` | resolve the correct local directory name for a page title |
| `POST` | `/spaces` | create a new space |
| `DELETE` | `/spaces/{space_id}` | permanently delete a space and all its pages |
| `POST` | `/spaces/{space_id}/pages` | create a page (add `parent_page_id` for a child page) |
| `PUT` | `/spaces/{space_id}/pages/{page_id}` | update a page title and/or content (markdown) |
| `DELETE` | `/spaces/{space_id}/pages/{page_id}` | soft-delete a page |

Write routes authenticate against Docmost automatically using
`DOCMOST_APP_URL`, `DOCMOST_USER_EMAIL`, and `DOCMOST_USER_PASSWORD` from
`.env`. Content is markdown in and out, and the update route supports
`operation: replace | append | prepend`.

## Prerequisites

Before setup, make sure you have:

1. a running Docmost environment with PostgreSQL - **v0.71.1 or later required** for content write operations to function correctly (see note below)
2. Docker and Docker Compose available on the server where this service will run
3. network access from this service container to the live Docmost PostgreSQL container
4. network access from your Copilot CLI machine to the published Docmost MCP URL
5. the Docmost database credentials or DSN

> **Docmost version requirement - v0.71.1+**
>
> Content write operations (creating and updating page content) require Docmost v0.71.1 or later.
> Earlier versions silently discard the content field, resulting in pages being created empty.
>
> Upgrading Docmost carries no risk to your existing page data. Docmost upgrades are
> non-destructive - your spaces, pages, and history are stored in PostgreSQL and are not
> affected by a container image update. To upgrade, pull the latest image and recreate
> the container:
>
> ```bash
> docker compose pull docmost && docker compose up -d docmost
> ```
>
> To check which version you are currently running:
>
> ```bash
> docker exec docmost cat /app/apps/server/package.json | grep '"version"' | head -1
> ```

## Full setup from start to finish

Two setup methods are available. Both result in the same running service.

### Option A: from the published Docker image (recommended)

Pull the image directly from GitHub Container Registry - no clone or build step needed:

```bash
mkdir -p /opt/docmost-mcp && cd /opt/docmost-mcp
```

Create a `docker-compose.yml`:

```yaml
services:
  docmost-mcp:
    container_name: docmost-mcp
    image: ghcr.io/isak-landin/docmost-mcp-api:latest
    restart: unless-stopped
    env_file: .env
    environment:
      DOCMOST_DB_HOST: ${DOCMOST_DB_HOST}
      DOCMOST_DB_PORT: ${DOCMOST_DB_PORT}
      DOCMOST_DB_NAME: ${DOCMOST_DB_NAME}
      DOCMOST_DB_USER: ${DOCMOST_DB_USER}
      DOCMOST_DB_PASSWORD: ${DOCMOST_DB_PASSWORD}
      LISTEN_HOST: ${LISTEN_HOST:-0.0.0.0}
      LISTEN_PORT: ${LISTEN_PORT:-8099}
      DOCMOST_APP_URL: ${DOCMOST_APP_URL}
      DOCMOST_USER_EMAIL: ${DOCMOST_USER_EMAIL}
      DOCMOST_USER_PASSWORD: ${DOCMOST_USER_PASSWORD}
    ports:
      - "${EXTERNAL_PORT:-8099}:${LISTEN_PORT:-8099}"
    networks:
      - docmost_network

networks:
  docmost_network:
    external: true
    name: ${DOCMOST_NETWORK_NAME:-docmost_default}
```

Then continue from [step 2](#2-confirm-the-shared-docker-network-name) below. Skip the build step - replace `docker compose up --build -d` with `docker compose up -d`.

---

### Option B: from source

Clone or copy the repository onto the same server that hosts the live Docmost deployment.

Example placeholder path:

```bash
mkdir -p /opt/docmost-mcp
cd /opt/docmost-mcp
```

Place the project files there.

### 2. Confirm the shared Docker network name

By default this project joins the Docker network named `docmost_default`.

Set `DOCMOST_NETWORK_NAME` in your `.env` if your Docmost stack uses a different network name:

```env
DOCMOST_NETWORK_NAME=my_custom_network
```

To find your Docmost network name:

```bash
docker network ls | grep docmost
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

DOCMOST_APP_URL=http://<DOCMOST_CONTAINER_NAME>:3000
DOCMOST_USER_EMAIL=<YOUR_DOCMOST_USER_EMAIL>
DOCMOST_USER_PASSWORD=<YOUR_DOCMOST_USER_PASSWORD>

DOCMOST_NETWORK_NAME=docmost_default

LISTEN_HOST=0.0.0.0
LISTEN_PORT=8099
EXTERNAL_PORT=8099

MCP_ALLOWED_HOSTS=<YOUR_DOCMOST_MCP_HOSTNAME>

MODE=prod
LOG_LEVEL=INFO
```

### 5. Build and start the container

**Option A (image):**

```bash
docker compose up -d
```

**Option B (source):**

```bash
docker compose up --build -d
```

This will:

1. pull the published image (Option A) or build from `Dockerfile` (Option B)
2. create or recreate the `docmost-mcp` container
3. attach it to the external Docker network set by `DOCMOST_NETWORK_NAME`
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

#### Write endpoints

Write routes require `DOCMOST_APP_URL` plus `DOCMOST_USER_*` in `.env`.
Authentication is transparent, and the full route list is in
[REST capabilities](#rest-capabilities).

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
additional remote MCP server you add to extend Copilot CLI with Docmost access.

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

Allow these tools:

```text
list_spaces
get_space
get_space_tree
get_replica_standards
resolve_replica_directory_name
get_replica_structure
list_pages
get_page
create_space
delete_space
create_page
update_page
delete_page
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
      "tools": [
        "list_spaces",
        "get_space",
        "get_space_tree",
        "list_pages",
        "get_page",
        "get_replica_standards",
        "resolve_replica_directory_name",
        "get_replica_structure",
        "create_space",
        "delete_space",
        "create_page",
        "update_page",
        "delete_page"
      ]
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
We are working with extremely complex and sensitive structures.
Therefor we can't afford your common assumptions and usual approach to be implemented.
It is essential that all following rules are followed.

Clarification. Internal documentation is not docs that exist in the repository you have access to. It is the copilot internal documentation for a session.

- Always read internal documentation before attempting to answer or take action.
- Always update internal documentation when new insight is established which does not match the current internal documentation.
- Always update internal documentation determined that previously mentioned additions, edits and deletes were accepted and not reflected in internal documentation.
- Don't Update documentation, project or internal, until change is implemented.
- Don't update project documentation unless asked for.
- Mention deprecated project documentation when noticed to be deprecated.
- Keep ownership boundaries strict.
- Do not push persistence into bootstrap.
- Prefer simple return contracts.
- Don't expect existence of code representation unless explicitly existing is mentioned or can be assumed.
- Don't guess or invent new rules or module ownerships.

## Docmost MCP - reading

Use the docmost-mcp MCP server as the primary long-term documentation source for the active project.
Remote Docmost pages are the authoritative long-term representation of the project - deprecation is not the default assumption.
Only treat a page as stale or outdated when there is a clear, verified conflict with current code or runtime behavior, not merely because a local replica was edited.

If documentation, documented behavior, page names, or relevant file/path references are mentioned without full context in the prompt, consult docmost-mcp before guessing.
Internal session documentation and Docmost documentation are complementary - use both. Neither replaces the other.
Always resolve the correct space first with list_spaces, then inspect pages within that space.
Pages are space-scoped and are not global lookups.
Use get_space_tree when you need the nested structure of a space.
Use list_pages for a flat listing. Use get_page for a single page with full markdown content.

## Local replica management

Maintain or create a local replica at `./{space_name}-replica/` when the client workflow requires it.
No spaces are allowed in any local replica directory or file name. Replace spaces with hyphens in all local paths (e.g. "Local LLM Helper" -> `Local-LLM-Helper-replica`).
Use get_replica_structure for the exact local replica layout of an existing space and for initial replica creation.
Use get_replica_standards and resolve_replica_directory_name to derive correct directory names for new local-only pages.
Use the replica tree mapping plus `_meta.json` to relate local replica files back to remote pages.

When local replica files are edited, track which files changed and which remote pages they correspond to.
Do NOT automatically sync local replica changes to remote Docmost. Only sync after the user has accepted the change - either explicitly (user says "sync" or "push") or implicitly (user states the change is final or the local version is correct).
Treat remote Docmost as potentially behind local-only edits until manual sync occurs, but do not treat it as deprecated.

## Docmost MCP - writing

The docmost-mcp MCP server supports write operations. Auth is handled automatically - never call an auth route first.
All content is markdown in and out.

Before creating a page, use get_space_tree or list_pages to check if a matching page already exists.
Use resolve_replica_directory_name and get_replica_standards to derive correct names for new pages before creating them.

Use create_page to create a new page. Pass parent_page_id to create a nested child page.
Use update_page to push local replica content changes to remote. Prefer update_page over delete+create - Docmost preserves page history on update.
Use delete_page ONLY when the user has clearly confirmed a page should be removed, or when a local edit makes it unambiguous that the page no longer exists (e.g. the local file was deliberately deleted and the user agreed). Never delete speculatively.
Use delete_space ONLY on explicit user instruction.

All IDs passed to write tools must originate from a live MCP tool response - never from memory, local files, or inference:
- space_id: from list_spaces or create_space
- parent_page_id: from list_pages, get_space_tree, or a prior create_page response
- A create_page id is valid as parent_page_id only within the same uninterrupted sequence - re-resolve via list_pages or get_space_tree if any deletion has occurred since that creation
- A 404 from any write tool means the given ID does not exist in live Docmost; use a read tool to resolve the correct ID and retry

<<<<<<< Updated upstream
=======
Content formatting rules (applies to all page content passed to create_page and update_page):
Do NOT use Unicode typographic characters in page content. These characters are not reliably rendered across all Docmost consumers and may appear as garbled text or question marks.
Forbidden characters and their plain-text replacements:
- em dash (-) -> use hyphen with surrounding spaces ( - ) or a plain hyphen (-)
- en dash (-) -> use a plain hyphen (-)
- right arrow (->) -> use the two-character sequence ->
- double arrow (=>) -> use the two-character sequence =>
- ellipsis (...) -> use three plain dots (...)
- curly quotes (" " ' ') -> use straight quotes (" and ')
When inline text separation is needed, use a plain hyphen (-) as the separator.

>>>>>>> Stashed changes
When syncing local -> remote:
1. Match local replica files to remote pages via _meta.json.
2. For edited files: call update_page with the new markdown content.
3. For new local-only files (no remote page id): call create_page, then record the returned id.
4. For files removed locally AND confirmed removed by the user: call delete_page.
5. Never delete remote pages based solely on a missing local file without user confirmation.

## Naming rules (spaces)

Space slugs must be alphanumeric with no spaces or dashes (e.g. "mydocs", not "my-docs").
Use get_replica_standards to verify naming conventions before creating spaces or pages.
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
  - use Docmost as the primary **long-term** documentation source (not assumed stale)
  - use both internal session docs and Docmost - neither replaces the other
  - check whether a page already exists before creating one
  - derive page/space names via `get_replica_standards` and `resolve_replica_directory_name`
  - use `update_page` for local->remote sync of edited content
  - use `create_page` with `parent_page_id` for nested child pages
  - **only delete** remote pages when the user has confirmed removal - never speculatively
  - prompt the user before syncing local replica changes to remote

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
4. the MCP config includes all intended tools (read + write)

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

## Intended lookup and write flow

This service is **space-first**.

1. use `list_spaces` or `GET /spaces` to identify the correct Docmost space
2. select the matching space by name, then use its `id` as `space_id`
3. use `get_space_tree(space_id)` or `GET /spaces/{space_id}/tree` for the full nested structure
4. use `list_pages(space_id)` or `GET /spaces/{space_id}/pages` for a flat list
5. use `get_page(space_id, page_id)` or `GET /spaces/{space_id}/pages/{page_id}` for a single page with markdown content

Before creating a page:
- check whether the page already exists via `get_space_tree` or `list_pages`
- derive the correct name with `get_replica_standards` and `resolve_replica_directory_name`
- use `create_page` with `parent_page_id` to create nested child pages at any depth

All IDs passed to write operations must originate from a live MCP tool response - never from memory, local files, or inference:
- `space_id` must come from `list_spaces` or `create_space`
- `parent_page_id` must come from `list_pages`, `get_space_tree`, or a prior `create_page` response
- A `create_page` response id is valid as `parent_page_id` only within the same uninterrupted sequence - if any deletion or space removal has occurred since that creation, re-resolve with `list_pages` or `get_space_tree` first
- A **404** from any write tool means the given ID does not exist in the live Docmost instance; resolve the correct ID via a read tool and retry

When updating existing pages:
- prefer `update_page` over delete+create - Docmost preserves full page history on update
- use `operation=replace` (default) to overwrite, `append` to add after, `prepend` to add before

Important clarifications:

- page lookup is not global; pages are always scoped to a space
- the tools and routes accept `space_id`, not a space name string
- if you only know a space name, resolve it through `list_spaces` first
- the tree is built dynamically from `pages.parent_page_id`
- `parent_page_id = null` means the page is a top-level page in the space
- `orphan_pages` contains pages whose parent is missing or unreachable

## Recommended documentation-source workflow

The intended usage is **not** merely "Docmost-related tasks."

The intended usage is:

- Docmost MCP is the primary **long-term** documentation source for the active project - remote pages are not presumed stale or deprecated
- established project direction, user decisions, and documented behavior should be read from Docmost when not fully present in the prompt
- internal session documentation and Docmost documentation are complementary - use both
- if the user refers to docs, documentation, a documented page, or a file/path that may be documented externally, check Docmost before guessing
- maintain a **local replica** of documentation at `./{space_name}-replica/` for local editing

Recommended local-replica behavior:

1. create a local replica location if it does not exist, at `./{space_name}-replica/`
2. use `get_replica_structure(space_id)` as the source for the initial replica layout
3. use `get_replica_standards()` and `resolve_replica_directory_name(...)` for new local-only pages not yet on remote
4. when local replica files are edited, track which files changed and which remote pages they correspond to
5. do **not** automatically sync local changes to remote - only sync after the user accepts the change (explicitly or implicitly)
6. to sync: use `update_page` for edited files, `create_page` for new local-only files, `delete_page` only when the user has confirmed a page should be removed
7. never delete remote pages based solely on a missing local file without user confirmation
8. treat remote Docmost as potentially behind local-only edits until sync occurs, but do **not** treat it as deprecated

## Replica structure and naming standard

Use the replica surfaces when you want the client to stop guessing local layout.

- use `get_replica_standards()` or `GET /replica/standards` for the shared policy
- use `get_replica_structure(space_id)` or `GET /spaces/{space_id}/replica-structure` for the full local layout of an existing remote space
- use `resolve_replica_directory_name(...)` or `GET /replica/resolve-directory-name` when creating a new local-only page directory that does not yet exist on remote

Replica root:

- root path: `./{space_name}-replica/`
- spaces in the space name are replaced with hyphens (e.g. "Local LLM Helper" -> `./Local-LLM-Helper-replica/`)
- no spaces are allowed in any local directory or file name

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

1. use the filesystem-safe page title as the base directory name - spaces are replaced with hyphens
2. if sibling pages collide at the same level, use `{title}__{slug_id}`
3. if `slug_id` is missing or still collides, use `{title}__{short_page_id}`
4. no spaces are allowed in any local directory or file name at any level

Sync and truth rule:

- remote Docmost is the long-term authoritative documentation source - not assumed stale
- the local replica is the editable working copy
- when local replica files are edited, call out the changed local file paths explicitly
- when those edited files correspond to remote pages, identify the remote page title and page id
- do not automatically sync local changes back to remote - only after user accepts the change
- to sync: use `update_page` for edits, `create_page` for new local-only pages, `delete_page` only when user confirms

The MCP server also publishes built-in instructions (from `app/mcp_server.py` `SERVER_INSTRUCTIONS`):

```text
This server exposes Docmost spaces and pages for both reading and writing.

## Reading
Use list_spaces to find the correct space. Use get_space_tree for page hierarchy.
Use list_pages for a flat page list. Use get_page for a single page with markdown content.
If the user gives a space name rather than a UUID, resolve it with list_spaces first.
Pages are always space-scoped - always pass space_id together with page_id.

## Writing
All write tools authenticate automatically - never call an auth tool first.
Use create_space to create a new space (slug must be alphanumeric, no dashes).
Use create_page to create a page. Pass parent_page_id to create nested child pages.
Use update_page to update an existing page's title and/or content.
  Prefer update_page over delete+create - Docmost preserves page history on update.
  Use operation='replace' (default) to overwrite, 'append' or 'prepend' to add content.
Use delete_page to soft-delete a page (it moves to Docmost trash).
Use delete_space to permanently delete a space and all its contents.
All content is markdown in and out. Never pass ProseMirror JSON to write tools.

Content formatting rules (applies to all page content passed to create_page and update_page):
Do NOT use Unicode typographic characters in page content. These characters are not reliably
rendered across all Docmost consumers and may appear as garbled text or question marks.
Forbidden characters and their plain-text replacements:
  em dash (-)    -> use hyphen with surrounding spaces ( - ) or a plain hyphen (-)
  en dash (-)    -> use a plain hyphen (-)
  right arrow (->) -> use the two-character sequence ->
  double arrow (=>) -> use the two-character sequence =>
  ellipsis (...)  -> use three plain dots (...)
  curly quotes (" " ' ') -> use straight quotes (" and ')
When inline text separation is needed, use a plain hyphen (-) as the separator.

All IDs passed to write tools (space_id, page_id, parent_page_id) must originate from a
prior MCP tool response in the current session - never from memory, local files, or inference.
  - space_id: must come from list_spaces or create_space.
  - parent_page_id: must come from list_pages, get_space_tree, or a create_page response.
A 404 from any write tool means the given ID does not exist in the live Docmost instance.
Resolve by calling the appropriate read tool (list_spaces, list_pages) to obtain a valid ID.

## Replica management
Maintain or create a local replica at `./{space_name}-replica/` when the client workflow allows it.
All local replica directory and file names must not contain spaces - replace with hyphens.
Use get_replica_structure for the initial local replica layout.
Use get_replica_standards and resolve_replica_directory_name for local-only additions.
When local replica files are edited, identify changed files, map them to remote pages,
and tell the user those changes still need manual sync back to remote Docmost.
Treat remote Docmost as potentially stale after local-only edits until manual sync.
If content looks stale, deprecated, or inconsistent with verified behavior, say so explicitly.
If requested data is missing, report that explicitly instead of guessing.
```

## Architecture

Typical deployment:

1. the live Docmost stack already exists on a server
2. this service runs as a separate container on that same server
3. this service joins the same Docker network as Docmost so it can reach the Docmost PostgreSQL container
4. Copilot CLI runs on a different machine and connects remotely to `https://<YOUR_DOCMOST_MCP_HOST>/mcp`

## Files in this project

Important files:

| File | Purpose |
|---|---|
| `Dockerfile` | builds the Docmost MCP image |
| `docker-compose.yml` | runs the Docmost MCP container |
| `env.example` | example runtime configuration |
| `requirements.txt` | Python dependencies |
| `app/main.py` | FastAPI application entrypoint |
| `app/mcp_server.py` | MCP server and all MCP tool definitions |
| `app/models.py` | shared Pydantic models for request/response |
| `app/docmost_auth/auth.py` | Docmost login; stores JWT in memory; never persisted |
| `app/query/docmost.py` | DB + REST read operations (spaces, pages, tree, replica) |
| `app/query/routers/` | REST GET routes for read operations |
| `app/write/docmost.py` | httpx REST client for all write operations |
| `app/write/routers/spaces.py` | POST/DELETE `/spaces` REST routes |
| `app/write/routers/pages.py` | POST/PUT/DELETE `/spaces/{id}/pages` REST routes |
| `docs/docmost-write-api.md` | Docmost write API notes (auth, POST-only, response wrapper) |

## Data model

**Spaces** - `public.spaces`

Columns exposed: `id`, `name`, `description`, `slug`, `visibility`, `default_role`,
`creator_id`, `workspace_id`, `created_at`, `updated_at`.

**Pages** - `public.pages`

Columns exposed: `id`, `slug_id`, `title`, `icon`, `position`, `parent_page_id`,
`creator_id`, `last_updated_by_id`, `space_id`, `workspace_id`, `is_locked`,
`content`, `created_at`, `updated_at`.

Deleted Docmost rows are excluded by checking `deleted_at IS NULL`.

## Known issues

**Page title duplication (fixed)** — `create_page` and `update_page` both pass `title` as
a dedicated field; Docmost renders it as the page header above the body. `SERVER_INSTRUCTIONS`
and tool descriptions now explicitly prohibit including the title as a `# Heading` in the
content body, which previously caused it to render twice. Pages created before this
instruction fix still carry a duplicate `# Heading` in their stored content — `update_page`
will not strip it automatically; content must be explicitly rewritten to remove it.

## License

See `LICENSE`.
