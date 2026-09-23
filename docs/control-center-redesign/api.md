# Control-center data contract

**Status:** implemented September 11, 2026.

## Browser-local progress

Completion progress remains version 2. Quiz attempts are stored separately in the same browser under `systems-inference-quiz-v1`:

```json
{
  "layer-1": {
    "task-0": {"answer": "true", "submitted_at": "2026-09-11T15:20:00.000Z"},
    "layer": {"answers": ["true", "false"], "score": 8, "submitted_at": "2026-09-11T15:25:00.000Z"}
  }
}
```

The task-card mapping is embedded in the static HTML/JavaScript and is deterministic: the first card in Layer 1 owns checkpoint 0, then the next card owns checkpoint 1, continuing in the existing document order through checkpoint 35. Existing version 1 and 2 progress imports continue unchanged. Quiz attempts do not alter a completion export or an import.

## Read-only vault API

`GET /api/learning-state` is unchanged. The live Sakethwiki panel remains in collapsed materials and retains its current bounded, read-only behavior.

## No new writes

There is no API for answers, notes, source edits, grading, or external submissions. Quiz attempts are browser-local only. The learner chooses where to keep the proof artifact or brief explanation.
