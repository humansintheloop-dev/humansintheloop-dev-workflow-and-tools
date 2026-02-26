You are repairing a generated implementation plan that must follow a strict task schema.

Fix ONLY the listed validation errors.
- Do NOT add new steel threads.
- Do NOT add new tasks unless required to fix a missing contract field on an existing task (prefer rewriting titles/structure).
- Do NOT change scope or introduce new features.
- Preserve numbering and ordering of tasks as much as possible.
- Ensure every task uses this format:

- [ ] **Task X.Y: Outcome-oriented description**
  - TaskType: OUTCOME | INFRA | REFACTOR
  - Entrypoint:
  - Observable:
  - Evidence:
  - Steps:
    - [ ] ...

Return the FULL corrected plan as markdown. No commentary.

Validation errors:
$VALIDATION_ERRORS

Plan to repair:
$PLAN_TEXT
