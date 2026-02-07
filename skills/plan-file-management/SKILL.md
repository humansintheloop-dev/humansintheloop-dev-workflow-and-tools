---
name: plan-file-management
description: Guidelines for structural operations on plan files (renumbering). Claude should use this skill when the user asks to renumber or fix numbering in a plan file, or after inserting, deleting, or reordering threads/tasks.
---

# Plan File Management

Structural operations on plan files such as renumbering threads and tasks.

## Renumbering Plan Files

When threads or tasks are added, removed, or reordered, fix numbering by running
the `fix-plan-numbering.py` script in this skill's `scripts/` directory:

    uv run skills/plan-file-management/scripts/fix-plan-numbering.py <path-to-plan-file>

Run this after:
- Inserting or deleting threads or tasks
- Rearranging plan sections
- When the user asks to renumber or fix numbering
