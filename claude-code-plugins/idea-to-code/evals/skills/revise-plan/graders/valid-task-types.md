---
type: regex
target: { source: file, path: docs/ideas/active/eval-idea/eval-idea-plan.md }
pattern: 'TaskType:(?! (OUTCOME|INFRA|REFACTOR)\s*$)'
flags: m
match: not_contains
---

Every TaskType line matches `TaskType: (OUTCOME|INFRA|REFACTOR)\s*$`: no TaskType line has any other value.
