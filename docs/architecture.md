# Live learning roadmap — architecture

Status: approved and implemented on September 8, 2026. Audience: Saketh, using the existing roadmap now.

Preserve index.html and its nine-layer study/experiment layout. Serve it from a loopback-only local service, alongside a read-only JSON endpoint. While the page is open, fetch current note metadata every 10 seconds with no overlapping requests. Show connection health, last successful scan, recent relevant notes, and their suggested curriculum layers. Keep the September 8 reviewed assessment and next reading visible, labeled with their review date. New notes appear as new evidence awaiting review; ingestion never establishes mastery.

Data flow: SakethVault/_wiki/cs Markdown → bounded read-only scanner → normalized evidence snapshot → same-origin GET /api/learning-state → live panel. A fixed curated topic map connects known notes to layers. Unknown notes remain unmapped; do not guess completion or silently move the learning position. No model calls on polling. A future semantic review mechanism is a separate decision.

Use the local vault directly; the SakethWiki README confirms it is the source of truth. No SakethWiki code changes, database access, public note upload, cloud deployment or hosted-to-local browser bridge. The site only works on this Mac while its service runs. Phone/remote access requires a separately designed private publishing/sync connection.

Risk classification: static presentation is speed-owned. File access, note provenance and polling are review-required because bugs could expose private files, misstate learning evidence or overlap work.

Invariants: never write to the vault; read only allowlisted Markdown beneath the configured canonical root; reject escaping symlinks; never expose arbitrary paths or serve the workspace wholesale. Escape all note text. Preserve all 36 logical checkpoints. Browser progress v2 stores a completion timestamp when the user selects a new checkpoint; v1 data is migrated without inventing past dates. Existing file-origin progress will not automatically appear on a localhost origin; implement explicit validated export/import, without overwriting destination progress unless the user confirms.

Only routes explicitly listed in api.md are served. No CORS. Validate Host and Origin where present; bind 127.0.0.1. A missing vault or parse error is visible, never a successful empty snapshot. Keep last good data marked stale. The browser retries through its normal bounded polling cycle.

Checks: fixture-based scan/filter/date tests, symlink and traversal rejection, malicious title escaping, partial files, inaccessible vault, stable ordering, concurrent-request prevention, stale/recovery behavior, restart behavior, and checkbox export/import validation. Do not run tests against writable real notes.

Rollback: stop local service, restore backed-up presentation files and remove the new service files. Vault has no writes to undo. Keep the existing browser progress and explicit export. No launch agent or always-on worker is installed in this scope.
