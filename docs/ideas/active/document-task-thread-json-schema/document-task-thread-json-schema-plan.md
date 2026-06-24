Now I have what I need. This is a Type C platform capability adding two JSON Schema files plus a SKILL.md update. Outputting the plan.

# Implementation Plan: Document Task and Thread JSON Schema

## Idea Type

**Type C — Platform/infrastructure capability.** Adds machine-readable JSON Schema artifacts to the `plan-file-management` skill so Claude Code agents can construct valid Task/Thread JSON for the `i2code plan` CLI on the first attempt.

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Overview

The work is implemented using TDD throughout. Each task starts by adding a failing test (a `pytest` test under `tests/` that validates the schema artifact's existence, JSON validity, structural shape, or actual `jsonschema`-based validation behavior) and ends by making it pass with the minimal artifact change.

Steel Thread 1 establishes the build/CI baseline: the project already has a working build and CI, so Task 1.1 verifies the existing suite passes before any change. Steel Threads 2–4 each introduce exactly one validation scenario from the spec — first the Task schema, then the Thread schema (with `$ref` to the Task schema), then the `SKILL.md` discoverability change. A final cleanup thread removes any transient validation fixtures created along the way (if test design keeps them, that thread will be empty and skipped — the plan only includes it if drift-prevention follow-up artifacts were created).

The plan never touches Python source under `src/i2code/` and never adds new dependencies to `pyproject.toml`. `jsonschema` is used only inside the test suite via `uvx jsonschema` invoked by tests, or via a dev-only import path that uses an existing test dependency if one is already present (the implementer must check `pyproject.toml` first; see Task 2.1 step 1).

## Steel Thread 1: Verify Existing Build and CI Pass

The repository already has a working `uv`-based Python build, a `pytest` test suite under `tests/`, and CI under `.github/workflows/`. Before adding any schema files, confirm the baseline is green so subsequent commits in this work can be attributed cleanly to the schema additions.

- [x] **Task 1.1: Existing test suite passes on a clean checkout**
  - TaskType: INFRA
  - Entrypoint: `uv run pytest`
  - Observable: `uv run pytest` collects the existing tests under `tests/` and exits with code 0; no schema-related tests have been added yet.
  - Evidence: `uv run pytest` exits 0 from a clean working tree (run the command, capture the last 20 lines of output, confirm exit code 0).
  - Steps:
    - [x] Run `uv run pytest` from the project root and confirm exit code 0
    - [x] Run `uvx pyright --level error src/` and confirm zero errors (matches the project pre-commit checklist)
    - [x] Record the baseline test count from `pytest` output so later threads can confirm new tests are additive

## Steel Thread 2: Task JSON Schema Validates Task JSON

Adds `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json` — the prescriptive contract for the JSON object that `i2code plan` accepts via `--task-file` and as items of `--tasks` / `--tasks-file`. After this thread, a Claude agent (or a developer) can validate a Task JSON blob against the schema and see required-field, type, enum, and minimum-length violations.

- [ ] **Task 2.1: `task.schema.json` exists, is valid JSON, and is a valid Draft 2020-12 schema**
  - TaskType: INFRA
  - Entrypoint: `uv run pytest tests/plan_file_management_schemas/test_task_schema.py -k schema_file_is_valid`
  - Observable: The file `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json` exists, parses as JSON, declares `"$schema": "https://json-schema.org/draft/2020-12/schema"`, declares `"$id": "task.schema.json"`, and passes Draft 2020-12 meta-schema validation.
  - Evidence: `uv run pytest tests/plan_file_management_schemas/test_task_schema.py -k schema_file_is_valid` exits 0; the test loads the file with `json.load`, asserts the `$schema` and `$id` values, and calls `jsonschema.Draft202012Validator.check_schema(...)` (using whichever JSON Schema validator is already available in the existing test environment — see step 1).
  - Steps:
    - [ ] Inspect `pyproject.toml` and confirm whether `jsonschema` is already an installed dependency for tests. If it is not present in `[project]` or `[dependency-groups]`, the test MUST invoke the validator via `subprocess.run(["uvx", "check-jsonschema", "--check-metaschema", path])` instead of importing `jsonschema` directly — this honors the "no new dependencies" constraint.
    - [ ] Create `tests/plan_file_management_schemas/__init__.py` (empty) and `tests/plan_file_management_schemas/test_task_schema.py`
    - [ ] In `tests/plan_file_management_schemas/test_task_schema.py`, add the failing test `test_schema_file_is_valid` that resolves the path `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json` relative to the repository root, loads the file with `json.load`, asserts `data["$schema"] == "https://json-schema.org/draft/2020-12/schema"`, asserts `data["$id"] == "task.schema.json"`, and validates the schema against the Draft 2020-12 meta-schema using the validator chosen in step 1
    - [ ] Run the test and confirm it fails because the schema file does not yet exist
    - [ ] Create `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json` with the exact content from the spec ("`task.schema.json` (exact content)" section)
    - [ ] Run the test and confirm it passes
    - [ ] Run `python -m json.tool < claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json` as a manual sanity check and confirm it prints reformatted JSON (no error)

- [ ] **Task 2.2: `task.schema.json` accepts a known-good Task and rejects malformed Tasks**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/plan_file_management_schemas/test_task_schema.py`
  - Observable: A Task JSON object containing exactly the six required fields with valid values validates successfully; Task JSON missing any required field, with an extra `description` property, with `steps: []`, or with `task_type: "REFACTOR"` is rejected by the schema with a non-zero validator outcome.
  - Evidence: `uv run pytest tests/plan_file_management_schemas/test_task_schema.py` exits 0; the test file contains one passing case (the known-good Task from the spec's Acceptance Criteria item 8) and four failing cases (missing required field, `additionalProperties` violation via extra `description`, empty `steps` array, `task_type: "REFACTOR"` enum violation) — each implemented as a separate `pytest` test that asserts validation succeeds or raises `jsonschema.ValidationError` (or, if using `check-jsonschema` via subprocess, asserts the return code).
  - Steps:
    - [ ] Add failing test `test_known_good_task_validates` that constructs the Task JSON object from spec Acceptance Criteria item 8 (the "Add health endpoint" object) and asserts it validates against `task.schema.json`
    - [ ] Add failing test `test_missing_required_field_rejected` that copies the known-good Task, deletes `evidence`, and asserts validation fails
    - [ ] Add failing test `test_additional_property_rejected` that copies the known-good Task, adds `"description": "extra"`, and asserts validation fails (this exercises `additionalProperties: false`)
    - [ ] Add failing test `test_empty_steps_rejected` that copies the known-good Task, sets `steps: []`, and asserts validation fails (this exercises `minItems: 1`)
    - [ ] Add failing test `test_refactor_task_type_rejected` that copies the known-good Task, sets `task_type: "REFACTOR"`, and asserts validation fails (this documents the spec's deliberate two-value enum)
    - [ ] Run the failing tests and confirm they fail in the expected way (any failure shape that proves the assertion ran; some may already pass if Task 2.1's schema content is correct — that's fine, the test still proves the contract)
    - [ ] Inspect the test failures; no code change is required if the schema from Task 2.1 already encodes the constraints correctly. If any test fails for a reason other than "validation succeeded when it should have failed" or vice versa, fix the schema (Task 2.1 file) so all five tests pass
    - [ ] Confirm all five tests in this file pass

## Steel Thread 3: Thread JSON Schema References Task Schema

Adds `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json`, whose `tasks[]` items use `{ "$ref": "task.schema.json" }`. After this thread, a Thread JSON blob can be validated end-to-end, including its embedded tasks, via the relative `$ref`.

- [ ] **Task 3.1: `thread.schema.json` exists, is valid JSON, and is a valid Draft 2020-12 schema**
  - TaskType: INFRA
  - Entrypoint: `uv run pytest tests/plan_file_management_schemas/test_thread_schema.py -k schema_file_is_valid`
  - Observable: The file `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json` exists, parses as JSON, declares `"$schema": "https://json-schema.org/draft/2020-12/schema"`, declares `"$id": "thread.schema.json"`, and passes Draft 2020-12 meta-schema validation.
  - Evidence: `uv run pytest tests/plan_file_management_schemas/test_thread_schema.py -k schema_file_is_valid` exits 0; the test asserts `$schema`, `$id`, and meta-schema validity using the same validator approach chosen in Task 2.1.
  - Steps:
    - [ ] Create `tests/plan_file_management_schemas/test_thread_schema.py`
    - [ ] Add the failing test `test_schema_file_is_valid` that loads `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json` and asserts `$schema`, `$id`, and meta-schema validity (mirroring the structure of `tests/plan_file_management_schemas/test_task_schema.py:test_schema_file_is_valid`)
    - [ ] Run the test and confirm it fails because the file does not yet exist
    - [ ] Create `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json` with the exact content from the spec ("`thread.schema.json` (exact content)" section)
    - [ ] Run the test and confirm it passes

- [ ] **Task 3.2: `thread.schema.json` accepts a known-good Thread (resolving `$ref` to `task.schema.json`) and rejects malformed Threads**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/plan_file_management_schemas/test_thread_schema.py`
  - Observable: A Thread JSON object with `title`, `introduction`, and a `tasks` array of one valid Task validates successfully (proving the relative `$ref: "task.schema.json"` resolves against the sibling file); a Thread missing any required field, with an extra property at the Thread level, with `tasks: []`, or whose embedded task is missing a required Task field is rejected.
  - Evidence: `uv run pytest tests/plan_file_management_schemas/test_thread_schema.py` exits 0; the test file validates the known-good Thread JSON from spec Acceptance Criteria item 8 and rejects four malformed variants. Validation uses a validator that resolves the `$ref` against the sibling `task.schema.json` file (in `jsonschema` this is a `Registry` populated from both files; in `check-jsonschema` it works automatically when both files share a directory).
  - Steps:
    - [ ] Add failing test `test_known_good_thread_validates` that constructs the Thread JSON from spec Acceptance Criteria item 8 (the "Spring Boot Application with Health Check" object containing one task) and asserts it validates against `thread.schema.json`. The test MUST configure the validator so the relative `$ref: "task.schema.json"` resolves to the sibling file; if using `jsonschema`, build a `jsonschema.Registry` containing both schemas keyed by their `$id`; if using `check-jsonschema` via subprocess, pass `--schemafile thread.schema.json` from the `references/` directory so sibling resolution works
    - [ ] Add failing test `test_missing_required_field_rejected` that deletes `introduction` from the known-good Thread and asserts validation fails
    - [ ] Add failing test `test_thread_additional_property_rejected` that adds `"summary": "extra"` to the known-good Thread and asserts validation fails
    - [ ] Add failing test `test_empty_tasks_rejected` that sets `tasks: []` and asserts validation fails
    - [ ] Add failing test `test_invalid_embedded_task_rejected` that mutates the embedded task to remove its `evidence` field and asserts validation fails (this proves the `$ref` is actually consulted)
    - [ ] Run the failing tests and confirm they fail in the expected way; if any fail because the schema content is wrong, fix the schema file from Task 3.1 (do not loosen the assertions)
    - [ ] Confirm all five tests in this file pass

## Steel Thread 4: SKILL.md Surfaces the Schemas

Inserts a `## Schemas` section into `SKILL.md` so a Claude session reading the skill top-to-bottom encounters the schemas before any command that consumes JSON. This is the discoverability acceptance criterion from the spec.

- [ ] **Task 4.1: `SKILL.md` contains a `## Schemas` section before `## fix-numbering` that links to both schema files and clarifies the `--tasks-file` array shape**
  - TaskType: OUTCOME
  - Entrypoint: `uv run pytest tests/plan_file_management_schemas/test_skill_md.py`
  - Observable: `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md` contains a top-level `## Schemas` heading; that heading appears before the `## fix-numbering` heading; the section text links to both `references/task.schema.json` and `references/thread.schema.json` using the relative paths shown in the spec; the section explicitly notes that `--tasks` / `--tasks-file` accept the *array* of Task objects (not a full Thread object).
  - Evidence: `uv run pytest tests/plan_file_management_schemas/test_skill_md.py` exits 0; the test reads `SKILL.md`, asserts the index of `## Schemas` is less than the index of `## fix-numbering`, asserts the section body contains the substrings `[references/task.schema.json](references/task.schema.json)`, `[references/thread.schema.json](references/thread.schema.json)`, and the clarifying phrase about `--tasks` / `--tasks-file` accepting the array.
  - Steps:
    - [ ] Create `tests/plan_file_management_schemas/test_skill_md.py`
    - [ ] Add failing test `test_schemas_section_present_before_fix_numbering` that reads `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md`, locates the line `## Schemas` and the line `## fix-numbering`, and asserts the `## Schemas` line index is strictly less than the `## fix-numbering` line index (and both are found)
    - [ ] Add failing test `test_schemas_section_links_both_files` that asserts the file content contains both `[references/task.schema.json](references/task.schema.json)` and `[references/thread.schema.json](references/thread.schema.json)`
    - [ ] Add failing test `test_schemas_section_clarifies_tasks_file_is_array` that asserts the section body contains a phrase clarifying that `--tasks` / `--tasks-file` accept the *array* of Task objects (assert the substring `tasks[]` and the word `array` appear in close proximity, OR assert the full sentence from the spec is present verbatim)
    - [ ] Run the three tests and confirm they fail because the `## Schemas` section has not yet been added
    - [ ] Edit `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md` to insert the `## Schemas` section verbatim from the spec ("`SKILL.md` modification" section) immediately after the introductory paragraph that ends with `i2code plan <subcommand> <plan_file> [options]` and before the existing `## fix-numbering` section. Do not modify any other text in `SKILL.md`
    - [ ] Run all three tests and confirm they pass

## Steel Thread 5: Confirm No Regressions and Full Suite Passes

Runs the full project test suite one more time to confirm no `src/i2code/` source was changed, no existing test was broken, and the new schema tests live alongside the existing tests. Also runs the type checker per the project pre-commit checklist.

- [ ] **Task 5.1: Full project test suite and type checker pass after schema additions**
  - TaskType: INFRA
  - Entrypoint: `uv run pytest && uvx pyright --level error src/`
  - Observable: `uv run pytest` exits 0 with at least the baseline test count from Task 1.1 plus the new tests added in Steel Threads 2–4 (12 new tests total: 5 in `test_task_schema.py`, 5 in `test_thread_schema.py`, 3 in `test_skill_md.py`, minus the 1 `schema_file_is_valid` test per file that overlaps the count — net: 13 new tests). `uvx pyright --level error src/` exits 0 with zero errors.
  - Evidence: `uv run pytest && uvx pyright --level error src/` exits 0 from a clean working tree; the pytest output shows the new `tests/plan_file_management_schemas/` tests collected and passing; `git diff --name-only origin/master..HEAD -- src/i2code/ pyproject.toml` prints nothing (no changes under `src/i2code/`, no changes to `pyproject.toml`).
  - Steps:
    - [ ] Run `uv run pytest` and confirm exit code 0 and the total test count is baseline + 13 (or more, accounting for the validator approach chosen in Task 2.1 step 1)
    - [ ] Run `uvx pyright --level error src/` and confirm zero errors
    - [ ] Run `git diff --name-only` against the merge base and confirm the only modified/added paths are `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md`, `claude-code-plugins/idea-to-code/skills/plan-file-management/references/task.schema.json`, `claude-code-plugins/idea-to-code/skills/plan-file-management/references/thread.schema.json`, and `tests/plan_file_management_schemas/**`
    - [ ] Run the CodeScene `pre_commit_code_health_safeguard` per the project memory's pre-commit checklist before the final commit

---

## Change History
### 2026-06-24 07:09 - mark-step-complete
uv run pytest exited 0 with 1442 passed, 4 xfailed (see logs/baseline-pytest.log)

### 2026-06-24 07:09 - mark-step-complete
uvx pyright --level error src/ exited 0 with 0 errors, 0 warnings, 0 informations (see logs/baseline-pyright.log)

### 2026-06-24 07:09 - mark-step-complete
Baseline test count recorded: 1442 passed, 4 xfailed (no schema-related tests yet)

### 2026-06-24 07:09 - mark-task-complete
Baseline INFRA task verified: pytest passes (1442 passed, 4 xfailed), pyright passes (0 errors). Baseline test count is 1442.
