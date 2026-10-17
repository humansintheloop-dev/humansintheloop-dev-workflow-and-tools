---
type: regex
target: last_message
pattern: 'TaskType:(?! (OUTCOME|INFRA|REFACTOR)\s*$)'
flags: m
match: not_contains
---

Every TaskType line matches `TaskType: (OUTCOME|INFRA|REFACTOR)\s*$`: no TaskType line has any other value.
