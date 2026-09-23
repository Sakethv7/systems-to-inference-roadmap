# Browser-local progress contract

The loopback API and vault-scanning contract are unchanged. This document covers only local browser progress.

## Version 2 export

```json
{
  "schema_version": 2,
  "storage_key": "systems-inference-curriculum-v2",
  "checkpoints": [
    {"done": true, "completed_at": "2026-09-11T15:20:00.000Z"},
    {"done": true, "completed_at": null},
    {"done": false, "completed_at": null}
  ]
}
```

## Validation

- exactly 36 checkpoint records
- `done` is boolean
- `completed_at` is `null` or a valid ISO timestamp
- `done: false` requires `completed_at: null`
- unknown schema versions are rejected

## Import compatibility

- v1 `{ checkpoints: boolean[] }` imports as v2 with `completed_at: null` for existing completed rows
- v2 retains timestamps
- the user sees the number of completion and timestamp changes before confirming

## Non-goals

No server persistence, user accounts, automatic vault inference, background writes, or public sharing.
