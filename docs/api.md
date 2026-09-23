# Live roadmap contracts 

GET / returns index.html. GET /api/learning-state returns JSON with schema_version=1, status (ok/partial/unavailable), scanned_at, last_success_at, snapshot_id, notes and warnings. Send Cache-Control: no-store. Note records contain id (relative identifier), title, entry_date (nullable), modified_at (change hint only), content_hash, layer_id (nullable), and evidence_state=stored. No absolute paths, raw note bodies, secrets or maturity scores are returned.

The UI's reviewed position and next reading come from the existing dated review, not from inference inside this endpoint. Display both review date and last scan time.

GET /health returns status without filesystem details. GET /index.html aliases the homepage and GET /live.js serves the live view script. All other routes return 404; non-GET/HEAD methods return 405. Never fall back to directory listing. Host must match the loopback service; cross-origin requests are rejected. Bound note count, file size and request duration; return explicit partial status when bounds are reached.

Progress export: `{schema_version: 2, storage_key: "systems-inference-curriculum-v2", checkpoints: [{done: boolean, completed_at: ISO timestamp or null}]}`. There are exactly 36 records. Version 1 `{schema_version: 1, storage_key: "systems-inference-curriculum-v1", checkpoints: [36 booleans]}` exports remain importable; their completed timestamps are recorded as unavailable. Reject unknown versions, wrong keys, wrong lengths, invalid timestamps, and completed timestamps on incomplete checkpoints. No import runs on page load; user action and confirmation are required.

Configuration: VAULT_PATH defaults to ~/SakethVault; bind is fixed to 127.0.0.1; port is configurable with a stable default to preserve the browser origin. No credentials, remote API calls or persisted derived database required.

Implementation bounds: at most 2,000 candidate files, 1 MiB per file and four seconds per scan; concurrent scans wait at most one second. Socket operations time out after eight seconds. Snapshot failures return HTTP 503; partial scans return 200 with explicit partial status. The conceptual directory is scanned directly (not recursively). Metadata parsing accepts scalar titles and ISO entry dates; incomplete/invalid UTF-8 notes are partial failures.
