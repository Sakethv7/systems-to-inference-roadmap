# Learning control-center logic flow

**Status:** implemented September 11, 2026.

```mermaid
flowchart TD
  A[Open local roadmap] --> B[Load existing progress]
  B --> C[Find first incomplete task in ordered layers]
  C --> D[Show its task card on Home]
  D --> E[Open current lesson]
  E --> F[Open primary material]
  F --> G[Do the named reading, build, or explanation]
  G --> H[Answer 1-2 task questions]
  H --> I{Evidence item true?}
  I -->|yes| J[Tick its existing checkbox]
  I -->|no| K[Leave unchecked and return later]
  J --> L{First three task cards marked?}
  L -->|yes| M[Answer ten-question layer quiz]
  M --> N[Create the named proof or evidence]
  N --> O[Manually tick fourth proof evidence when true]
  L -->|no| D
  O --> P[Save progress and quiz attempt]
  P --> Q[Update layer count, history, and next task]
```

## Rules

1. One task maps to one existing checkbox; no task or quiz can silently complete another.
2. The primary link is sufficient to start. Alternate material is optional and collapsed.
3. A task check has one or two questions. A layer assessment has ten questions. Both show immediate feedback and record attempts locally.
4. The proof task asks for an explanation, trace, diagram, measurement, or test result in the learner's own notes. It is not automatically graded.
5. A `Build` or `Practice` task may link to a coding or design exercise, but it remains part of the current layer.
6. A completed checkbox can be unticked; its existing timestamp behavior remains unchanged.
