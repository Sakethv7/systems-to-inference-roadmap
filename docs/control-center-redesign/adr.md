# ADR: represent the roadmap as linked learning tasks

**Status:** implemented September 11, 2026.

## Decision

Reuse each existing canonical checkbox as the completion state for one task card. A task card binds the checkbox to the relevant reading, experiment, or explanation. It does not create another completion model. Store separately scoped browser-local quiz attempts for immediate task feedback and a ten-question layer assessment.

## Why

The learner needs to answer: what do I do now, where do I go, why does it matter, and what do I mark when it is done. A task card answers these questions in one view.

## Alternatives rejected

- Add a new task database and a second set of checkmarks: creates conflicting completion counts.
- Treat a quiz score as completion: rewards guessing and creates a false mastery claim.
- Use 10–20 questions after every task and another 10–20 at the layer boundary: converts a practical curriculum into a 26–36 question test per layer.
- Turn every source into a full lesson in the page: recreates the dense reference document.
- Keep coding and system-design hubs as primary navigation: makes the learner choose a track instead of completing the current systems task.

## Compatibility and recovery

The existing 36 checkbox indices, v1 migration behavior, v2 timestamps, export/import format, and import confirmation continue to apply. Quiz attempts use their own browser-local key and are intentionally separate from completion progress. An answer never writes to the vault or marks a checkbox. The existing backup and exported progress remain rollback paths.
