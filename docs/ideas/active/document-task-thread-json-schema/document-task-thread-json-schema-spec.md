# Platform Capability Specification: Document Task and Thread JSON Schema

## Classification

**Type C — Platform/infrastructure capability.** This spec enhances the `idea-to-code` plugin's `plan-file-management` skill, which is consumed by Claude Code sessions invoking the `i2code plan` CLI.

## Purpose and Context

The `plan-file-management` skill exposes several `i2code plan` subcommands that accept JSON input for tasks and threads. Today the JSON shape is described only in scattered prose inside `SKILL.md` (e.g., one command says *"see spec for schema"*; others list field names in a sentence). There is no authoritative artifact a Claude Code agent can read to construct correct JSON on the first attempt.

This capability adds machine-readable JSON Schema files (Draft 2020-12) that describe the Task and Thread JSON shapes as a prescriptive contract for Claude, and surfaces them from `SKILL.md`.

## Consumers

1. **Claude Code agents invoking `plan-file-management`** — the primary consumer. Agents read `SKILL.md`, follow the link to a schema file, and use the schema (plus per-field `description` text) to construct JSON for `--tasks`, `--tasks-file`, `--steps`, or `--task-file`.
2. **Human developers maintaining the skill** — secondary consumer. The schemas are a single source of truth for the JSON contract, so prose in `SKILL.md` does not have to re-state every field.
3. **Future runtime validators** — out of scope for this idea, but the artifacts are positioned so the Python CLI (or its tests) could later import them via `jsonschema` without restructuring.

## Capabilities and Behaviors

The capability MUST provide:

1. **A `Task` schema** (`references/task.schema.json`) defining the JSON object accepted by `--task-file` and the items of the `--tasks` / `--tasks-file` arrays.
2. **A `Thread` schema** (`references/thread.schema.json`) defining a Thread object whose `tasks` field references the Task schema.
3. **A discoverable entry point in `SKILL.md`** so a Claude agent reading the skill finds the schemas before generating JSON.

The capability MUST NOT:

- Modify any Python source under `src/i2code/`.
- Add or change any CLI command, argument, or runtime behavior.
- Add new dependencies (no `jsonschema` package added).
- Add per-command inline schema links in `SKILL.md` (top-level section only).

## High-Level APIs, Contracts, and Integration Points

### File layout

```
claude-code-plugins/idea-to-code/skills/plan-file-management/
├── SKILL.md                 (modified)
└── references/              (new directory)
    ├── task.schema.json     (new)
    └── thread.schema.json   (new)
```

### Schema dialect and conventions

- All schemas use Draft 2020-12: `"$schema": "https://json-schema.org/draft/2020-12/schema"`.
- Each schema declares a relative `$id` equal to its file name (`"$id": "task.schema.json"`, `"$id": "thread.schema.json"`) so the files are self-contained and `$ref` resolution within the directory works without a base URL.
- Both schemas set `"additionalProperties": false`.
- Every property carries a one-line `"description"`.

### `task.schema.json` (exact content)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "task.schema.json",
  "title": "Task",
  "description": "A single task accepted by `i2code plan` task-mutating commands. Used as the body of --task-file and as each item of the --tasks / --tasks-file arrays.",
  "type": "object",
  "additionalProperties": false,
  "required": ["title", "task_type", "entrypoint", "observable", "evidence", "steps"],
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable, outcome-oriented task title (text after `Task X.Y:` in the rendered plan)."
    },
    "task_type": {
      "type": "string",
      "enum": ["INFRA", "OUTCOME"],
      "description": "Verification category of the task. OUTCOME = introduces externally observable behavior. INFRA = enables build/test/run but does not introduce user-visible behavior on its own."
    },
    "entrypoint": {
      "type": "string",
      "minLength": 1,
      "description": "Exact shell command or execution path that runs the task (rendered as the `Entrypoint:` line, backticked)."
    },
    "observable": {
      "type": "string",
      "minLength": 1,
      "description": "Precise, testable description of what changes when the entrypoint runs (stdout, exit code, file written, branch created, etc.)."
    },
    "evidence": {
      "type": "string",
      "minLength": 1,
      "description": "Exact shell command that proves the observable via the entrypoint (rendered as the `Evidence:` line, backticked)."
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "minLength": 1,
        "description": "Single implementation step description, rendered as an unchecked `- [ ] ...` sub-bullet."
      },
      "description": "Ordered list of implementation step descriptions. Each becomes an unchecked checklist item under the task."
    }
  }
}
```

### `thread.schema.json` (exact content)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "thread.schema.json",
  "title": "Thread",
  "description": "A complete steel thread accepted by `i2code plan` thread-mutating commands (insert-thread-before/after, replace-thread).",
  "type": "object",
  "additionalProperties": false,
  "required": ["title", "introduction", "tasks"],
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "description": "Steel thread title (rendered as the text after `Steel Thread N:`)."
    },
    "introduction": {
      "type": "string",
      "minLength": 1,
      "description": "Multi-paragraph prose introducing the thread (rendered between the thread header and the first task)."
    },
    "tasks": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "task.schema.json" },
      "description": "Ordered list of Task objects. Tasks are renumbered automatically by the CLI; the JSON does not carry task numbers."
    }
  }
}
```

### `SKILL.md` modification

A new `## Schemas` section MUST be inserted immediately after the introductory paragraph that ends with `i2code plan <subcommand> <plan_file> [options]` and before the existing `## fix-numbering` section. The section text is:

```markdown
## Schemas

JSON arguments to the commands below MUST conform to these schemas:

- [references/task.schema.json](references/task.schema.json) — the object passed via `--task-file` and the items of the `--tasks` / `--tasks-file` arrays.
- [references/thread.schema.json](references/thread.schema.json) — the object passed via no single flag today; its `tasks[]` array is what `--tasks` / `--tasks-file` accept, and its `title` / `introduction` fields correspond to the `--title` / `--introduction` flags on `insert-thread-before`, `insert-thread-after`, and `replace-thread`.

The schemas are the source of truth for field names, required-ness, and value constraints (including the `task_type` enum). The per-command sections below describe how each command consumes these objects but do not re-state the schema.
```

No other text in `SKILL.md` is changed. Existing prose such as *"The file must contain a JSON object with `title`, `task_type`, `entrypoint`, `observable`, `evidence`, and `steps` fields"* is left intact for this iteration (removing the redundancy is a future cleanup, out of scope here).

## Non-Functional Requirements

| Concern | Requirement |
|---|---|
| **Correctness** | Every required field in each schema MUST correspond to a field actually accessed by `Task.create` / `Thread.create` in `src/i2code/plan_domain/`. No schema field may name something the domain model ignores. |
| **Determinism** | Schemas are static files; no generation step. Reading the same file twice MUST yield byte-identical content. |
| **Validatability** | Each `.schema.json` file MUST itself be valid JSON (parseable by `python -m json.tool`) AND a valid Draft 2020-12 schema (passes `jsonschema`'s meta-schema if a developer runs the check locally — no CI enforcement required). |
| **Discoverability** | A Claude session that reads `SKILL.md` from top to bottom MUST encounter the `## Schemas` section before any command that takes JSON input. |
| **Footprint** | The skill directory adds exactly one subdirectory (`references/`) containing exactly two files. No other files (READMEs, indexes) are added. |
| **No regressions** | `i2code plan --help` and every existing `i2code plan` subcommand MUST behave identically before and after this change. Existing tests under `tests/` MUST continue to pass without modification. |

There are no latency, throughput, or availability SLAs — the capability is a static documentation artifact.

## Scenarios and Workflows

### Primary end-to-end scenario

**Scenario P1: Claude generates a valid `--task-file` JSON for `insert-task-after`.**

1. A user asks Claude to add a new task to thread 2 of a plan file.
2. Claude reads `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md`.
3. Claude sees the `## Schemas` section and reads `references/task.schema.json`.
4. Using the schema's `required` list, property types, `enum` for `task_type`, and per-field `description` text, Claude composes a JSON object with all six fields populated correctly (e.g., `task_type` is either `INFRA` or `OUTCOME`, `steps` is a non-empty array of non-empty strings, no extra fields).
5. Claude writes the JSON to a file in the idea directory and invokes `i2code plan insert-task-after <plan_file> --thread 2 --after 1 --task-file <path> --rationale "..."`.
6. The CLI's existing field-presence check in `task_cli._load_task_from_file` succeeds and the task is inserted.

### Supporting scenarios

**S1: Claude generates a valid `--tasks-file` JSON for `insert-thread-after`.** Claude reads `thread.schema.json`, follows the `$ref` to `task.schema.json` for the `tasks[]` item shape, and produces a JSON file containing only the array (because the `--tasks-file` flag accepts an array of Task objects, not a full Thread object — `--title` / `--introduction` come from separate flags). The `## Schemas` section explicitly calls this out so Claude does not mistakenly wrap the array in a Thread object.

**S2: Schema parses cleanly.** A developer runs `python -m json.tool < references/task.schema.json` and `python -m json.tool < references/thread.schema.json`; both succeed.

**S3: `$ref` resolves.** A developer runs a one-off check (e.g., `jsonschema -i sample-thread.json references/thread.schema.json`) against a sample thread that embeds a valid task; validation succeeds because the relative `$ref: "task.schema.json"` resolves against the sibling file.

**S4: Strictness rejects malformed input.** A developer validates a Task JSON that includes an extra `description` field, or a `steps: []`, or `task_type: "REFACTOR"`. Each is rejected by the schema (`additionalProperties: false`, `minItems: 1`, `enum` violation respectively). This documents the contract; it does not change CLI behavior because runtime validation is out of scope.

## Constraints and Assumptions

### Constraints

- **No Python changes.** The Python CLI keeps its current hand-rolled field-presence check in `src/i2code/plan/task_cli.py::_load_task_from_file`. The schemas are documentation only.
- **No new dependencies.** Do not add `jsonschema` or any other package to `pyproject.toml`.
- **No CI step.** No automated validation of the schemas in CI for this iteration.
- **`task_type` enum is two values.** The schema specifies `enum: ["INFRA", "OUTCOME"]` to match what `SKILL.md` advertises today, even though `src/i2code/prompt-templates/create-implementation-plan.md` defines a three-value canonical set (`OUTCOME`, `INFRA`, `REFACTOR`). Reconciling that discrepancy is explicitly out of scope and tracked as a future follow-up (see "Known Limitations").
- **No per-command inline links.** Only the top-level `## Schemas` section links to the schema files. Per-command sections in `SKILL.md` are not modified.

### Assumptions

- The `plan-file-management` skill is the right home for these files (rather than a shared `references/` elsewhere). The skill is already self-contained; no other skill consumes Task/Thread JSON.
- A relative `$ref: "task.schema.json"` inside `thread.schema.json` is resolvable by every JSON Schema validator a developer is likely to use locally, given the schemas live in the same directory.
- Claude readers honor `additionalProperties: false`, `minLength`, `minItems`, and `enum` when constructing JSON — i.e., the schema's strictness translates into prescriptive behavior, not just rejection at validation time.
- The list of JSON-accepting commands in `SKILL.md` (the seven mentioned in the Purpose section) is complete and stable for the duration of this work; no new JSON-accepting subcommand is being added in parallel.

## Acceptance Criteria

The capability is complete when ALL of the following hold:

1. **Files present.** The repository contains:
   - `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json`
   - `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json`
2. **Schemas are valid JSON.** `python -m json.tool` parses each file without error.
3. **Schemas are valid Draft 2020-12 schemas.** Each file declares `"$schema": "https://json-schema.org/draft/2020-12/schema"` and conforms to the meta-schema (verifiable locally via the `jsonschema` library; not enforced in CI).
4. **Task schema content matches this spec.** All six required fields (`title`, `task_type`, `entrypoint`, `observable`, `evidence`, `steps`) are present with the types, constraints, descriptions, and enum specified in the "`task.schema.json` (exact content)" section above. `additionalProperties: false` is set.
5. **Thread schema content matches this spec.** All three required fields (`title`, `introduction`, `tasks`) are present with the types, constraints, descriptions specified. `tasks.items` uses `{ "$ref": "task.schema.json" }`. `additionalProperties: false` is set.
6. **`SKILL.md` updated.** The `## Schemas` section is inserted at the location specified ("immediately after the introductory paragraph … before `## fix-numbering`") and contains links to both schema files plus the clarifying note that `--tasks` / `--tasks-file` accept the *array* (not a full Thread object).
7. **No regressions.** No Python source under `src/i2code/` is modified; no entry is added to `pyproject.toml`; the existing test suite (`uv run pytest`) passes unchanged.
8. **Sample round-trip.** A small ad-hoc validation (run manually or in a transient test) successfully validates a known-good Task JSON object against `task.schema.json` and a known-good Thread JSON object against `thread.schema.json`. Concrete known-good objects:

   ```json
   {
     "title": "Add health endpoint",
     "task_type": "OUTCOME",
     "entrypoint": "./gradlew bootRun",
     "observable": "GET /actuator/health returns 200 with {\"status\":\"UP\"}",
     "evidence": "curl -fsS http://localhost:8080/actuator/health",
     "steps": ["Add HealthController", "Wire route", "Add integration test"]
   }
   ```

   ```json
   {
     "title": "Spring Boot Application with Health Check",
     "introduction": "Stand up the service and confirm it responds to actuator health probes.",
     "tasks": [
       {
         "title": "Add health endpoint",
         "task_type": "OUTCOME",
         "entrypoint": "./gradlew bootRun",
         "observable": "GET /actuator/health returns 200",
         "evidence": "curl -fsS http://localhost:8080/actuator/health",
         "steps": ["Add HealthController", "Wire route", "Add integration test"]
       }
     ]
   }
   ```

## Known Limitations (Out of Scope, Tracked for Follow-Up)

- **`REFACTOR` task type.** `create-implementation-plan.md` defines `REFACTOR` as a third canonical task type, but the schema enum here is `["INFRA", "OUTCOME"]` to match `SKILL.md` as-is. A separate follow-up should decide whether `SKILL.md` and the schema should both add `REFACTOR`.
- **No runtime CLI validation.** The schemas exist as documentation only. A future idea could swap `task_cli._load_task_from_file`'s ad-hoc field check for `jsonschema`-based validation with richer error messages.
- **Redundant prose in `SKILL.md`.** Per-command sentences still list field names (e.g., *"a JSON object with `title`, `task_type`, …"*). Removing that redundancy in favor of "see `references/task.schema.json`" is a documentation cleanup, deferred.
- **No drift test.** Nothing prevents the schemas from falling out of sync with `src/i2code/plan_domain/task.py` and `thread.py` if a future change adds a domain field. A future idea could add a test that compares schema `properties` against dataclass fields.
