# Local private-app data contract

**Status:** implemented locally September 11, 2026. iPad-access changes proposed September 22, 2026.

## New loopback routes

| Route | Method | Purpose |
|---|---|---|
| `/api/coverage` | GET | Coverage and gaps for each task, without raw note content. |
| `/api/decisions` | GET | Manual review/continue/skip/start decisions. |
| `/api/decisions` | PUT | Replace one validated manual decision. |
| `/api/progress` | GET | Durable checkpoint and quiz state. |
| `/api/progress` | PUT | Replace validated app-owned progress state. |

All routes are loopback-only, JSON, no-store, and reject unexpected origins and methods.

## SQLite tables

- `app_state(id, progress_json, quiz_json, evidence_json, updated_at)`
- `coverage_snapshot(note_id, title, entry_date, content_hash, layer_id, concepts_json, matched_at)`
- `learning_decision(task_id, decision, note_ids_json, rationale, created_at, updated_at)`

`app_state.progress_json` stores exactly 36 checkpoint records with `done` and `completed_at`. `app_state.quiz_json` stores quiz selections and submitted scores. `app_state.evidence_json` stores short learner-written evidence notes keyed to course tasks. `learning_decision.decision` is one of `review`, `continue`, `skip_reading_and_prove`, or `start_new`. A decision cannot set checkpoint completion.

---

## Proposed: iPad-access contract changes

### Configuration

| Name | Where | Contract |
|---|---|---|
| `APP_ALLOWED_HOSTS` | env var → `server.py` (via `compose.yaml`) | Comma-separated extra hostnames, no scheme, no port, e.g. `sakeths-mac.tail1234.ts.net`. Unset or empty means only `127.0.0.1:<port>` and `localhost:<port>` are accepted, exactly as today. |

### Request admission — `allowed()`

A request is admitted when **all** hold:

| Check | Loopback host (`127.0.0.1:<port>`, `localhost:<port>`) | Allowlisted host (from `APP_ALLOWED_HOSTS`) |
|---|---|---|
| `Host` header | exactly one of the two | exactly the name, or the name with `:443` |
| `Origin` header, if present | `http://` + Host | `https://` + name |
| `Sec-Fetch-Site` | not `cross-site` | not `cross-site` |

Otherwise: `403 {"error": "Cross-origin access denied"}` (unchanged shape).

Invariant: with `APP_ALLOWED_HOSTS` unset, every existing test in `tests/test_server.py` passes unchanged.

### `PUT /api/progress` — version check

Request body gains one optional field:

```json
{
  "checkpoints": [ /* 36 × {done: bool, completed_at: string|null} */ ],
  "quiz_attempts": {},
  "evidence_notes": {},
  "base_updated_at": "2026-09-22T18:04:11.482913+00:00"
}
```

| Case | Response |
|---|---|
| `base_updated_at` absent | `200`, write applied (compatibility; same as today). |
| `base_updated_at` equals stored `updated_at`, or nothing stored yet | `200 {"schema_version": 1, "checkpoints", "quiz_attempts", "evidence_notes", "updated_at"}` with the new `updated_at`. |
| `base_updated_at` differs from stored `updated_at` | `409 {"schema_version": 1, "error": "stale_write", "checkpoints", "quiz_attempts", "evidence_notes", "updated_at"}`. Nothing is written. |
| `base_updated_at` present but not a string | `400 {"error": "Invalid app progress"}` |

Invariants:
- The compare and the write happen inside the existing `self.lock` and one SQLite transaction, so two concurrent PUTs cannot both pass the check.
- `updated_at` is ISO-8601 UTC with microseconds and strictly changes on every successful write.

`GET /api/progress` is unchanged. It already returns `updated_at`, which the client stores as its next `base_updated_at`.

### New static assets

| Path | Content-Type | Source file |
|---|---|---|
| `/manifest.webmanifest` | `application/manifest+json` | `manifest.webmanifest` |
| `/icon.png` | `image/png` | `assets/saketh-learning-icon.png` (1254×1254, served as-is) |

Both go through `allowed()` like every other route. The `Dockerfile` `COPY` line must include them.

Manifest content:

```json
{
  "name": "Saketh Learning",
  "short_name": "Learning",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#eef2ee",
  "theme_color": "#133a35",
  "icons": [{ "src": "/icon.png", "sizes": "1254x1254", "type": "image/png", "purpose": "any" }]
}
```

`index.html` `<head>` additions: `<link rel="manifest" href="/manifest.webmanifest">`, `<link rel="apple-touch-icon" href="/icon.png">`, `<meta name="apple-mobile-web-app-capable" content="yes">`, `<meta name="apple-mobile-web-app-title" content="Learning">`, `<meta name="theme-color" content="#133a35">`.

### Client contract (`index.html`)

- Store `updated_at` from every `GET` or `200 PUT` response and send it as `base_updated_at`.
- On `409`: replace `progress`, `quizAttempts`, `evidenceNotes` from the body, re-render, and show "Updated on another device — reloaded."
- On `visibilitychange` to visible or window `focus`: if dirty, save first; otherwise `GET /api/progress` and adopt it only if its `updated_at` differs from the stored one. (Compare for inequality, not "newer": the stored value may be an older seconds-resolution string, which does not sort correctly against microsecond strings.)
- On `pagehide` or becoming hidden: flush a pending save immediately, using `fetch(..., {keepalive: true})` so it survives the page unloading.
- On touch devices (`@media (pointer: coarse)`), buttons, nav links, quiz options, checkbox rows and `<summary>` are at least 44 CSS px tall. Mac layout is unchanged.

### Tests to add (`tests/test_server.py`)

1. Allowlisted host with an `https://` origin → 200; the same host with an `http://` origin → 403; an unlisted host → 403.
2. Env unset → an allowlisted-looking host is rejected (fails closed).
3. PUT with a matching `base_updated_at` → 200 and a new `updated_at`; a second PUT reusing the old base → 409 with current state and no write.
4. PUT without `base_updated_at` → 200 (compatibility).
5. `/manifest.webmanifest` and `/icon.png` → 200 with the right content types.

### Manual acceptance check (after implementation)

On the iPad, with the Mac awake: open the tailnet URL, Add to Home Screen, launch from the icon (no Safari bar). Tick a checkpoint on the iPad, then switch to the Mac app. The tick appears there without a manual reload. Type on the Mac while the iPad sits on a stale copy, then edit on the iPad. The iPad shows the reload message and no Mac edit is lost.
