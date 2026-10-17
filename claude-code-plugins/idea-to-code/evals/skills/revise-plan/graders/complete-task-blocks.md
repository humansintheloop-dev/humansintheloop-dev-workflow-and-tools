---
type: llm
focus: { source: file, path: docs/ideas/active/eval-idea/eval-idea-plan.md }
---

Every task block has TaskType, Entrypoint, Observable, Evidence and at least one step.

A task block starts with a line like `- [ ] **Task X.Y: ...**`. PASS if every task block has a `TaskType:` line, an `Entrypoint:` line, an `Observable:` line, an `Evidence:` line, and a `Steps:` line followed by at least one `- [ ]` step. FAIL if any task block is missing one of these. Judge only whether the lines are present, not the quality of their content.
