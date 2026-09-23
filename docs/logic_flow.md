# Live roadmap logic 

1. Start a loopback service with the configured vault root and fixed routes.
2. Load the existing roadmap and its locally stored completion state.
3. Request a fresh snapshot of allowed conceptual notes. Scan only Markdown under _wiki/cs; omit known test fixtures and backups. Read frontmatter and substantive dated entries; modification time is only a change hint.
4. Normalize note titles, source-relative identifiers, entry dates and hashes. Associate only recognized topics with curriculum layers. Return unmapped notes explicitly. Do not treat generated maturity scores as user achievement.
5. Render new evidence separately from the dated reviewed position and next reading. Never check a completion box automatically.
6. After the prior request finishes, wait 10 seconds before the next poll. Cancel/ignore stale requests, pause on hidden tabs and refresh on focus.
7. On failure, retain last successful data labeled stale. On recovery replace it with a complete successful snapshot. Partial scans report partial status and do not remove previously observed evidence silently.
8. Export/import manual completion only on user action; accept the legacy 36-boolean v1 format and the timestamped v2 format, preview differences and require confirmation before replacing destination progress.

Verification must include normal refresh, duplicate content, malformed notes, disappearance during reads, service interruption, restart, hidden-tab polling and non-overlapping requests.
