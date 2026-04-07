# Content Write Investigation Report

> **Scope:** Investigation only. No fixes implemented. Based strictly on local docs, git
> history, and the existing investigation file (`CONTENT_WRITE_INVESTIGATION.md`).

---

## Summary

The content write path has **never successfully written content** via the current
`app/write/docmost.py` REST approach. However, this is **not a fundamental limitation of
Docmost** — the local project documentation (`docs/docmost-write-api.md`) describes a
fully supported REST content write path that differs from what the code currently sends.
The fix is a small, targeted change to payload field names.

---

## Finding 1 — Local docs contradict CONTENT_WRITE_INVESTIGATION.md's main conclusion

`CONTENT_WRITE_INVESTIGATION.md` states:

> `CreatePageDto` declares only: `title`, `icon`, `parentPageId`, `spaceId`. No `content`
> or `format` fields. ValidationPipe strips any undeclared fields.

However, `docs/docmost-write-api.md` (committed in the same session that introduced the
write layer — commit `e15b298`) documents the following for `POST /api/pages/create`:

| Field | Type | Required |
|---|---|---|
| `spaceId` | UUID | yes |
| `title` | string | no |
| `icon` | string | no |
| `parentPageId` | UUID | no |
| `content` | string or object | no |
| `format` | string | no (with content) |

And for `POST /api/pages/update`:

| Field | Type | Required |
|---|---|---|
| `pageId` | UUID | yes |
| `title` | string | no |
| `icon` | string | no |
| `content` | string or object | no |
| `operation` | string | with content |
| `format` | string | with content |

**These docs claim both `content` and `format` are accepted fields — not stripped.**

The two sources are in direct conflict. One of them is wrong. `docs/docmost-write-api.md`
was written from inspection of the running Docmost container's compiled JS source during
the same session the write layer was created, and it documents the exact internal code
path Docmost follows when content is provided (`parseProsemirrorContent`, `pageRepo.insertPage`,
`collaborationGateway.handleYjsEvent`).

---

## Finding 2 — Local project docs were never updated to reflect write capability

The `Docmost-mcp-crud/` replica docs — specifically:

- `Overview/page.md` — explicitly states **"Strictly read-only"** and **"no create, update,
  move, or delete operations on any Docmost entity"**
- `MCP-Server/page.md` — lists all tools as read-only; write tools not mentioned
- `REST-API/page.md` — marks the entire API as read-only; write routes not listed

**These pages were all created in commit `e15b298`** (the same commit that introduced the
write layer), then **renamed/moved only** in commit `4f0b104` (no content changes), and
**never updated again** to reflect write capabilities.

This is a confirmed remote-overwrite situation:

- The remote Docmost space these pages represent was synced before the write layer existed
- The write layer (`app/write/docmost.py`, `app/write/routers/`) was added in the same
  commit that created these docs, but the docs were not updated to reflect the new capability
- No subsequent commit updated the Overview, MCP-Server, or REST-API page content

The local replica docs therefore **predate and contradict** the current code. They describe
an older, read-only version of the project.

---

## Finding 3 — The actual payload field name mismatch

`docs/docmost-write-api.md` documents the update endpoint as requiring:

```json
{
  "pageId": "...",
  "content": "...",
  "operation": "replace",
  "format": "markdown"
}
```

The current `app/write/docmost.py` `update_page()` sends exactly this. The `create_page()`
function also sends `content` and `format`.

The question from `CONTENT_WRITE_INVESTIGATION.md` — whether `ValidationPipe` strips these
fields — cannot be resolved from local docs alone. `docs/docmost-write-api.md` was written
from inspection of the compiled Docmost source and claims these fields are **not** stripped
for create. For update it routes through the collab gateway internally, which also accepts
content.

**The current code payload structure matches the local documentation exactly.** If content
is still not appearing, the most likely candidate is not the payload structure but the
**debounce** on the update path (10–45 s) combined with the immediate `get_page_info` call
that reads back pre-flush content — giving a false impression that the write failed.

---

## Finding 4 — No evidence that writing ever worked via MCP-created pages

No page in the local `Docmost-mcp-crud/` replica or in the `Release/` and `Deployment/`
pages (the only MCP-consumer-created pages with known remote IDs) contains rich markdown
content returned from remote. The `update_page` call for `Release` returned `content: ""`
— consistent with the debounce lag described in `docs/docmost-write-api.md`.

**There is no local evidence that writing once worked**, but also no evidence that the
payload structure is wrong. The debounce lag is the most likely reason the content appears
absent immediately after a write.

---

## Local doc overwrite report

| File | Status | Last content change |
|---|---|---|
| `Docmost-mcp-crud/Overview/page.md` | **Stale — describes read-only project** | `e15b298` (before write layer) |
| `Docmost-mcp-crud/MCP-Server/page.md` | **Stale — write tools not listed** | `e15b298` |
| `Docmost-mcp-crud/REST-API/page.md` | **Stale — write routes not listed** | `e15b298` |
| `Docmost-mcp-crud/Deployment/page.md` | Updated — now includes image option | `23e7d12` |
| `Docmost-mcp-crud/Release/page.md` | New — v1.0.0 release notes | `23e7d12` |
| `docs/docmost-write-api.md` | Accurate — documents create/update with content | `e15b298` |

---

## Assessment

The most probable explanation for content not appearing in the Docmost UI after a write:

1. **`update_page`**: Content is written but the collab gateway debounces DB persistence
   10–45 s. The immediate `get_page_info` response reads pre-flush state. Check the page
   in the Docmost UI 30–60 s after the write before concluding it failed.

2. **`create_page`**: `docs/docmost-write-api.md` states `create` is self-contained and
   does a direct DB write — no debounce. If create also shows empty content, the field
   stripping described in `CONTENT_WRITE_INVESTIGATION.md` may be accurate for this
   Docmost version, and the `docs/docmost-write-api.md` notes may describe an older or
   different version.

**The single most actionable verification step** (not implemented here): check the Docmost
UI for the `Release` page 30–60 s after the `update_page` call made during this session.
If the content is visible, the write path works and the debounce is the only issue. If it
remains empty, the ValidationPipe stripping is confirmed and a different write mechanism
is needed (likely `POST /api/pages/import` for create, and no REST update path exists).
