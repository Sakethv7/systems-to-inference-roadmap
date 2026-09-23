# Calm course-progress experience

## Problem

Implemented September 11, 2026.

## Primary screen

1. **Continue learning**: one card with the reviewed current layer, one next reading, one experiment, and a single `Open this lesson` action.
2. **Course outline**: nine compact module rows showing `Not started`, `In progress`, or `Complete`; only the selected module expands.
3. **Selected module**: four clearly worded checkpoint rows. A row has a completion control, its purpose, and `Review material` / `Revisit experiment` links. Selecting a row records completion; it does not claim mastery.
4. **Your learning history**: completed rows grouped by module. New completions show a timestamp. Existing progress migrated from the old format says `Previously marked complete — date unavailable`.
5. **Notes and optional tracks**: live vault notes, interview drills, ML bridge, and safety-control material move behind secondary sections. They stay available without competing with the next lesson.

## State boundary

Progress stays browser-local. The vault remains read-only. The reviewed position remains a separate editorial assessment. A note in the vault never marks a checkpoint complete.

The existing 36 logical checkpoints remain canonical. The proposed progress state retains a timestamp per checkpoint so the history is truthful about new selections while not fabricating historical dates.

## Visual direction

Use a quiet single-column course surface: compact header, generous spacing, one main card, no repeated dashboard panels, and disclosure sections for optional material. The first viewport should show the learner where they are and one action to continue.
