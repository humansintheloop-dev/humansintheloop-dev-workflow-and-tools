# Discussion: Document Task and Thread JSON Schema

## Initial Idea

Enhance `claude-code-plugins/idea-to-code/skills/plan-file-management`:

- In a `references/` subdirectory document the JSON schema for tasks and threads
- Update the skill to reference the schema in the `references/` subdirectory

## Codebase Analysis

**Skill location**: `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md`
- Only file in skill; no `references/` subdirectory exists.
- Several commands accept JSON via `--tasks`, `--tasks-file`, `--steps`, or `--task-file`.
- SKILL.md describes fields in prose (e.g., *"The file must contain a JSON object with `title`, `task_type`, `entrypoint`, `observable`, `evidence`, and `steps` fields"*) and once mentions *"see spec for schema"* — but no schema document exists.

**Domain model** (`src/i2code/plan_domain/`):
- `Task` fields: `title` (str), `task_type` (`INFRA` | `OUTCOME`), `entrypoint` (str), `observable` (str), `evidence` (str), `steps` (list[str]).
- `Thread` fields: `title` (str), `introduction` (str), `tasks` (list[Task]).
- `Task.create` requires all metadata fields; `task_cli._load_task_from_file` validates presence of all six `_TASK_SPEC_FIELDS`.

**Commands that take JSON arguments**:
- `insert-thread-before` / `insert-thread-after` / `replace-thread`: `--tasks` (JSON array of task objects) or `--tasks-file`.
- `insert-task-before` / `insert-task-after` / `replace-task`: `--steps` (JSON array of step strings) plus individual flags, OR `--task-file` (JSON object).

## Q&A

### Q1: What format should the schema documentation use?

**Options offered**: JSON Schema (Draft 2020-12) / Markdown with table + example / Both / TypeScript-style interface.

**Answer**: **JSON Schema (Draft 2020-12)** — machine-readable `.schema.json` files. Standard, tool-friendly, and could later be used for programmatic validation in the CLI.

### Q2: How should the schema files be organized in `references/`?

**Options offered**: Two files (task + thread) / One combined with `$defs` / Three files (task + tasks-array + thread).

**Answer**: **Two files: task + thread**. Separate `task.schema.json` and `thread.schema.json`; the thread schema uses `$ref` to point at the task schema.

### Q3: How should SKILL.md reference the schemas?

**Options offered**: Inline links per command / Top-level Schemas section / Both.

**Answer**: **Top-level Schemas section** near the top of SKILL.md linking to both files. Individual command sections stay terse.

### Q4: Should this idea also wire the schemas into the CLI for runtime validation, or is the scope purely documentation?

**Options offered**: Documentation only / Docs + CLI validation / Docs + drift tests.

**Answer**: **Documentation only**. Add schema files and update SKILL.md; no Python changes. The CLI keeps its current ad-hoc field-presence checks in `task_cli._load_task_from_file`. Smallest, safest change.

### Q5: Given the goal is to tell Claude what JSON to produce, how strict should the schemas be?

**Clarification from user**: The goal of the schemas is to tell Claude Code the structure of the JSON it should provide. The schemas are *prescriptive guidance for Claude*, not a description of what the CLI silently tolerates.

**Options offered**: Fully strict / Strict on unknowns, permissive on empties / Strict + include examples.

**Answer**: **Fully strict**. `additionalProperties: false` on both Task and Thread; `minLength: 1` on all string fields; `minItems: 1` on `steps` and `tasks`; `task_type` constrained to `enum: ["INFRA", "OUTCOME"]`. Claude won't invent extra fields, won't emit blank strings, won't produce empty step lists.

## Classification

**Type: C — Platform/infrastructure capability**

**Rationale**: The change enhances the `idea-to-code` plugin's `plan-file-management` skill — a piece of developer-facing platform infrastructure that other Claude Code sessions consume. It is not a user-facing feature (no end-user UI/workflow change), not an architecture POC (no architectural concern being validated), and not an example repository. Its purpose is to make a platform capability (the `i2code plan` CLI's JSON-accepting commands) more correctly usable by the agent that drives it.

## Derived defaults (no question needed)

- **Schema dialect**: JSON Schema Draft 2020-12 (`"$schema": "https://json-schema.org/draft/2020-12/schema"`).
- **`$id`**: relative file name (`"$id": "task.schema.json"` etc.) so the schemas are self-contained inside the skill folder.
- **Thread's `tasks` field**: typed via `{ "type": "array", "items": { "$ref": "task.schema.json" }, "minItems": 1 }`.
- **Field `description`s**: every property gets a one-line `description` so Claude reads the intent next to the type — this is the whole point of the doc.
- **Examples**: omitted from the schemas themselves (user chose "Fully strict" without examples).
- **Array shape (`--tasks` / `--tasks-file`)**: documented in the SKILL.md Schemas section as "an array of `task.schema.json` objects" rather than a third schema file.

### Q6: Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?

**Answer**: No.

### Q7: How should the `task_type` enum be defined, given the discrepancy discovered during spec drafting?

**Context**: While preparing the spec, found that `src/i2code/prompt-templates/create-implementation-plan.md:222-275` defines the canonical task types as **OUTCOME, INFRA, REFACTOR** (three values) — not the `INFRA|OUTCOME` documented in SKILL.md. The Python CLI does not enforce an enum.

**Options offered**: Three values / Two values (as Q5) / Three values + descriptive text.

**Answer**: **Two values (as captured in Q5)** — `enum: ["INFRA", "OUTCOME"]`. The schema documents what SKILL.md currently advertises. Bringing `REFACTOR` into the skill is treated as a separate follow-up, out of scope for this idea.

