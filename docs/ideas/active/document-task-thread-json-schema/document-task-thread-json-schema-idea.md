# Idea: Document Task and Thread JSON Schema

## Summary

Add machine-readable JSON Schema (Draft 2020-12) documentation for the Task and Thread JSON shapes that the `i2code plan` CLI accepts, so Claude Code knows exactly what JSON to produce when invoking the `plan-file-management` skill.

## Motivation

The skill at `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md` describes several commands that accept JSON input — `insert-thread-before/after`, `replace-thread`, `insert-task-before/after`, `replace-task` — via `--tasks`, `--tasks-file`, `--steps`, or `--task-file`. The schema is only described in scattered prose (e.g., *"see spec for schema"*, or a sentence listing field names). There is no authoritative artifact Claude can reference to build correct JSON the first time.

## Scope

**Add:**

- `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json`
- `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json`

**Modify:**

- `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md` — add a top-level `## Schemas` section near the top that links to both schema files and notes that the `--tasks` / `--tasks-file` arguments expect an array of `task.schema.json` objects.

**Out of scope:**

- No Python code changes. The CLI keeps its current field-presence checks in `src/i2code/plan/task_cli.py::_load_task_from_file`. Wiring the schemas into the CLI as a runtime validator is a possible future follow-up, not part of this idea.

## Schema design

- **Dialect**: JSON Schema Draft 2020-12.
- **Two files** with `$ref` between them — `thread.schema.json` references `task.schema.json` for its `tasks[]` items.
- **Fully strict** as a prescriptive contract for Claude:
  - `additionalProperties: false` on both Task and Thread.
  - `minLength: 1` on every string field.
  - `minItems: 1` on `steps` and `tasks` arrays.
  - `task_type` constrained to `enum: ["INFRA", "OUTCOME"]`.
- Every property carries a one-line `description` so Claude reads field intent alongside its type.

### Task fields (derived from `src/i2code/plan_domain/task.py`)

`title`, `task_type` (`INFRA`|`OUTCOME`), `entrypoint`, `observable`, `evidence`, `steps[]` — all required.

### Thread fields (derived from `src/i2code/plan_domain/thread.py`)

`title`, `introduction`, `tasks[]` — all required; `tasks[]` items conform to `task.schema.json`.

## Classification

**Type C — Platform/infrastructure capability.** Enhances a plugin/skill that other Claude Code sessions consume; not a user-facing feature, architecture POC, or example.
