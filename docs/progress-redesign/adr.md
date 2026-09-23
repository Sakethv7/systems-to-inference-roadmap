# ADR: replace the checklist wall with a course-progress view

**Status:** approved and implemented September 11, 2026.

## Decision

Replace the top-level progress board and dense navigation with a course outline and one active lesson. Introduce version 2 of the browser-local progress format so newly completed checkpoints retain their completion time.

## Why

A course outline answers three immediate questions without asking the learner to infer structure:

- Where am I?
- What should I do next?
- What have I already done, and where can I revisit it?

## Alternatives rejected

- **Keep the current board and add more filters:** adds controls without solving orientation.
- **Infer completion from Sakethwiki notes:** turns topic exposure into a false mastery claim.
- **Store history remotely:** adds a privacy and account boundary without a user need.

## Compatibility and recovery

Existing `systems-inference-curriculum-v1` data migrates locally to v2. Each existing `true` becomes `done: true, completed_at: null`; the UI labels this date as unavailable. Old exports remain importable. A v2 export can restore timestamps. The old state remains untouched until the migrated state is saved successfully.

Recovery is an exported progress file and removal of the new v2 local key. No vault data, server API, or external system is changed.
