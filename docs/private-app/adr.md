# ADR: durable local state and reviewed knowledge coverage

**Status:** implemented locally September 11, 2026.

## Decision

Use SQLite owned by the local app for durable progress, quiz attempts, coverage snapshots, and manual learning decisions. Preserve browser export/import as a recovery and migration path.

## Why

Browser storage cannot reliably follow a user between the file page, localhost, and the private hosted site. A local database gives the Mac-local app a stable source of truth while keeping the Sakethwiki boundary private.

## Rejected alternatives

- Hosted app reads the vault directly: impossible without exposing a local service or creating a separately approved sync path.
- Treat a matching note as permission to skip: topic exposure is not demonstrated understanding.
- Store raw notes in the learning database: duplicates the vault and increases privacy/recovery risk.

## Recovery

SQLite is app-owned. Existing v1/v2 progress imports update browser state and then sync to the local app when the loopback server is open. Deleting `data/learning-app.sqlite3` resets only app progress, quiz state, coverage snapshots, and manual decisions; the vault remains untouched.

---

# ADR 2: reach the Mac from the iPad through Tailscale, not a hosted copy

**Status:** proposed September 22, 2026.

## Context

Saketh wants to use the learning app on an iPad. The vault and SQLite file live on the Mac. The app is loopback-only by design, so today no other device can reach it.

## Options

| Option | How it works | Main cost |
|---|---|---|
| A. Bind to LAN (`0.0.0.0`) | iPad connects over home Wi-Fi to the Mac's local IP. | Anyone on the same Wi-Fi (cafés, campus) can reach an unauthenticated server that holds private data. Only works at home. Plain HTTP. |
| **B. Tailscale serve (chosen)** | Tailscale forwards HTTPS from the Mac's tailnet name to loopback. | Mac must be awake with Docker and Tailscale running. Adds a dependency on Tailscale. |
| C. Hosted app + cloud database | Deploy the page and store progress in e.g. Supabase; the Mac pushes coverage summaries. | New deployment, auth, a second copy of private data off the Mac, and a sync component. Much bigger than the need. |
| D. Offline-first iPad cache | Service worker caches the page; iPad edits queue locally and merge when the Mac is reachable. | Needs a merge strategy for two devices editing the same record. Can be layered on B later. |
| E. Native iPad app | SwiftUI app wrapping a web view pointed at B's URL. | Needs Xcode signing; free signing expires every 7 days. Gives nothing B's home-screen app does not. |

## Choice

**B.** It is the smallest change that keeps the core privacy property: the process only listens on loopback, and only devices on Saketh's Tailscale account can get a request to it. It also works away from home, which A does not.

## Consequences and what is given up

- **Given up: availability when the Mac is unavailable.** Asleep, off, Docker stopped, or Tailscale stopped means the iPad shows a connection error. Option D is the upgrade path if this proves annoying.
- **Given up: "loopback-only" as a complete description of who can reach the app.** The server now trusts that Tailscale admits only Saketh's devices. If the tailnet is ever shared with another person, their devices could read and write progress unless open question 2 in `architecture.md` is implemented.
- **Given up: zero third-party dependency on the access path.** Tailscale's coordination server must be reachable to set up connections. Traffic is end-to-end encrypted and does not pass through Tailscale in readable form.
- **Kept:** no new open port on the Mac, no data leaves the Mac except over the encrypted tailnet to Saketh's iPad, vault still mounted read-only, Mac app unchanged.
- **New operational requirement:** the Mac's "prevent automatic sleeping when the display is off" power setting. Saketh changes it; it is a system setting.

---

# ADR 3: reject stale progress writes instead of last-write-wins

**Status:** proposed September 22, 2026.

## Context

`PUT /api/progress` replaces the whole state: all 36 checkpoints, all quiz attempts, all evidence notes. With one client, that is fine. With two, it silently loses data. Example: the Mac app has been open since morning. On the iPad you tick two checkpoints. Then you type one character in an evidence note on the Mac. The Mac sends its morning copy of everything, and the two iPad ticks disappear.

The underlying idea is **optimistic concurrency control**: instead of locking, each writer says which version it started from. The server accepts the write only if that is still the current version. Otherwise the writer must reload and try again.

## Options

| Option | Cost |
|---|---|
| Keep last-write-wins | Silent data loss as described above. |
| Per-field PATCH endpoints with merging | Correct, but a much larger API and client rewrite. |
| **Version check on the existing PUT (chosen)** | One new request field and one new 409 response. The losing client reloads, and at most loses the few seconds of typing it had not yet sent. |
| Refetch on focus only | Makes conflicts rare but not impossible. Used together with the chosen option, not instead. |

## Choice

The client sends `base_updated_at`, the `updated_at` value it last received. The server compares it with the stored `updated_at` inside the same lock that performs the write. On a mismatch it returns `409` with the current state. The client adopts that state, re-renders, and shows "Updated on another device — reloaded." The page also refetches progress whenever it becomes visible (`visibilitychange`), so switching devices normally starts from fresh state and a 409 is rare.

## Consequences and what is given up

- **Given up: keystrokes typed during a conflict.** If both devices edit within the same moment, the second writer's unsent change is discarded rather than merged. It is shown the fresh state and can retype. Per-field merging was judged not worth the rewrite.
- **Compatibility:** a request without `base_updated_at` is accepted as today, so older cached pages and the import flow keep working. This leaves a hole: an old client can still overwrite. It closes once the updated `index.html` is loaded everywhere.
- `updated_at` becomes a version token and must change on every write. It already does, but at one-second ISO resolution; two writes in the same second would share a value. The implementation must use microsecond resolution.
