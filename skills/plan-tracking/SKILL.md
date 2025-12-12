---
name: plan-tracking
description: Guidelines for working with plan files. Claude should use this skill when the user provides a plan file (e.g., *-plan.md) to ensure task completion is tracked in the plan file itself, not just internally.
---

# Plan File Tracking Guidelines

When working from a plan file (markdown file with task checkboxes), follow these guidelines to ensure proper tracking.

## Core Rule

**The plan file is the source of truth for task completion status.**

Update the plan file checkboxes (`- [ ]` to `- [x]`) immediately after completing each task. Do NOT rely on internal tracking (like TodoWrite) as a substitute for updating the actual plan file.

## Workflow

For each task in the plan:

1. Read the task from the plan file
2. Implement the task (write test, implement code, verify)
3. **Immediately update the plan file** - change `- [ ]` to `- [x]`
4. Continue to the next task

## Why This Matters

- The plan file is visible to the user and persists across sessions
- Internal tracking (TodoWrite) is ephemeral and not visible in the codebase
- Commits should include both the implementation AND the updated plan
- Other developers can see progress by looking at the plan file

## Common Mistake

BAD:
```
Complete task 1.1
Update internal TodoWrite
Complete task 1.2
Update internal TodoWrite
... (plan file never updated)
```

GOOD:
```
Complete task 1.1
Edit plan file: change "- [ ] 1.1" to "- [x] 1.1"
Complete task 1.2
Edit plan file: change "- [ ] 1.2" to "- [x] 1.2"
```

## When to Apply

Apply this guideline when:
- User provides a plan file path (e.g., `*-plan.md`, `*-tasks.md`)
- User says "follow the plan" or "implement from the plan"
- Working with any markdown file containing `- [ ]` task checkboxes

## Commit Guidelines

When committing completed tasks:
1. Stage the implementation changes
2. Stage the updated plan file (with checkbox marked)
3. Commit together so the commit reflects both the work done and the progress tracked
