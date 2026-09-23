# Verification — September 8, 2026

Implemented after design approval. Final diff review covered index.html changes against backups/2026-09-08-pre-live/index.html plus the new server.py/live.js routes, scanner and UI consumers.

14 Python regression tests passed: allowlisted routes, HEAD, rejected origins/methods, source edit reflected without restart, bounds, concurrent-scan timeout, entry dates, read-only behavior, disappearing file, missing vault, malformed-note recovery, restart-stable snapshot, symlink escape and directory rejection, unknown dates and unmapped/test filtering.

Browser tests passed against the running local service and isolated browser storage: real vault connection; nine layers and 36 checkpoints; exact original checkbox ordering; reload persistence; export/import round trip; invalid import rejection; preview/cancel/explicit apply; malicious title treated as text; retained evidence on partial/failure; recovery; 10-second polling; no overlapping requests; pause while hidden and refresh on visibility. Desktop 1440×1000 and mobile 390×844 have no horizontal overflow or page errors. Visual screenshots are in qa-live/.

Live snapshot: status ok; 166 conceptual notes; 17 explicit roadmap mappings. Service restarted successfully after final backend changes. Vault was read only; synthetic mutations used temporary test fixtures.

Limits/assumptions: this is a Mac-local service, manually restarted after reboot. Only direct conceptual Markdown files in _wiki/cs are live-scanned. Unknown topics need review. Scalar Markdown metadata and ISO entry dates are supported; generated maturity values are not mastery evidence. The dated reviewed assessment does not change with each note; the existing daily review remains separate. Obsidian links require the local SakethVault registration. Browser-origin progress transfers are explicit. No remote publication or automatic OS startup was configured.

Recovery: stop the local service; restore selected presentation changes from the before-live backup if needed. Preserve subsequent edits and exported progress. There are no vault writes or cloud changes to roll back.
