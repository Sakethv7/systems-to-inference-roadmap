# ADR: live view of local learning evidence

Status: approved and implemented on September 8, 2026.

Keep the existing standalone website and add a small read-only local service. Poll every 10 seconds while visible, pause when hidden, refresh on focus. This provides near-real-time evidence without cloud upload or a background model request per note edit.

Reject cloud-only hosting for this first slice: a hosted page cannot read this Mac's vault without an additional sync component. Reject a daily automation as the live-data transport: it cannot deliver near-real-time updates. Leave the existing daily review in place until the user approves whether to retain it for semantic assessment or remove it; it is not the live feed.

Separate live evidence from reviewed recommendations. Deterministic title/topic matching cannot reliably assess understanding or select a prerequisite to skip. Existing reviewed position remains until a review explicitly updates it. Recent unmatched notes are visible as unmapped evidence.

Tradeoff: local access requires the Mac and service to be running. Browser completion storage is origin-specific; use explicit export/import to move existing progress. Remote access and continuously generated recommendations are outside this first slice.
