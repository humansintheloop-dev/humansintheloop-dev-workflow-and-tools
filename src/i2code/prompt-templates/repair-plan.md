You are repairing a generated implementation plan.

Use `idea-to-code:plan-format`.

Fix ONLY the listed validation errors.
- Do NOT add new steel threads.
- Do NOT add new tasks unless required to fix a missing contract field on an existing task (prefer rewriting titles/structure).
- Do NOT change scope or introduce new features.
- Preserve numbering and ordering of tasks as much as possible.
- Resolve any "X or Y" / "X (or Y)" alternatives in tasks or steps — every decision must be committed to a single action, not left ambiguous for the coding agent.

Output the FULL corrected plan to stdout in markdown. No commentary.

Validation errors:
$VALIDATION_ERRORS

Plan to repair:
$PLAN_TEXT
