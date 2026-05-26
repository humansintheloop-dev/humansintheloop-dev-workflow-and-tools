# Specification: File-Based Input for Plan CLI Commands

## Purpose and Background

The `i2code plan` CLI provides commands to insert, replace, and manage threads and tasks within markdown plan files. These commands are primarily invoked by AI coding agents (e.g., Claude Code) that modify plans programmatically during implementation workflows.

Currently, file-based input (`--tasks-file`) exists only on the `replace-thread` command. The remaining thread-creation commands (`insert-thread-before`, `insert-thread-after`) and all single-task commands (`insert-task-before`, `insert-task-after`, `replace-task`) require all content to be passed as inline CLI options. For tasks with multi-line content — step descriptions, observable outcomes, entrypoint commands — inline options are error-prone and unwieldy.

## Target Users

**AI coding agents** (Claude Code, similar tools) that invoke `i2code plan` commands to modify plan files during implementation. These agents generate task JSON as intermediate artifacts and pass them to the CLI.

## Problem Statement

1. **Inconsistent `--tasks-file` support.** `replace-thread` supports `--tasks-file` as an alternative to `--tasks`, but `insert-thread-before` and `insert-thread-after` do not. The shared `_thread_spec_options` decorator in `thread_cli.py:12-20` only defines `--title`, `--introduction`, and `--tasks` (no file alternative). The `_resolve_tasks_json` helper at `thread_cli.py:23-34` exists but is only called from `replace_thread_cmd`.

2. **No file-based input for single-task commands.** `insert-task-before`, `insert-task-after`, and `replace-task` use `_task_spec_options` (`task_cli.py:12-23`) which requires six individual options: `--title`, `--task-type`, `--entrypoint`, `--observable`, `--evidence`, `--steps`. There is no way to provide all fields from a single JSON file.

## Goals

- Make `--tasks-file` available on all thread-creation commands, matching the existing `replace-thread` pattern.
- Provide a `--task-file` option on single-task commands so an entire task definition can be read from one JSON file.
- Maintain backward compatibility — all existing inline options continue to work unchanged.

## In Scope

- Add `--tasks-file` to `insert-thread-before` and `insert-thread-after` (2 commands).
- Add `--task-file` to `insert-task-before`, `insert-task-after`, and `replace-task` (3 commands).
- Mutual exclusivity enforcement and error messages for conflicting options.
- Tests for all affected commands.

## Out of Scope

- File-based input for arbitrary string options (e.g., `--introduction-file`, `--rationale-file`).
- Override/merge semantics (e.g., `--task-file` provides defaults, CLI options override individual fields).
- New file formats (YAML, TOML). JSON only.
- Changes to `delete-thread`, `delete-task`, `reorder-threads`, `reorder-tasks`, `move-task-before`, `move-task-after`, or any `mark-*` commands (these don't create threads or tasks).

## Functional Requirements

### FR-1: `--tasks-file` on insert-thread commands

Add a `--tasks-file` option to `insert-thread-before` and `insert-thread-after` with the following behavior:

- **Type:** `click.Path(exists=True)` — Click validates the file exists before the command runs.
- **Mutual exclusivity:** `--tasks` and `--tasks-file` are mutually exclusive. Providing both produces an error. Providing neither produces an error.
- **Resolution:** Use the existing `_resolve_tasks_json` helper to resolve the tasks JSON string from either source.
- **JSON format:** Same as existing `--tasks` — a JSON array of task objects:

```json
[
  {
    "title": "Task name",
    "task_type": "INFRA",
    "entrypoint": "`command`",
    "observable": "What to observe",
    "evidence": "`verification command`",
    "steps": ["Step 1", "Step 2"]
  }
]
```

- **Error messages:** Follow the existing pattern in `_resolve_tasks_json`:
  - Both provided: `"{command_name}: --tasks and --tasks-file are mutually exclusive"`
  - Neither provided: `"{command_name}: either --tasks or --tasks-file is required"`

### FR-2: `--task-file` on single-task commands

Add a `--task-file` option to `insert-task-before`, `insert-task-after`, and `replace-task` with the following behavior:

- **Type:** `click.Path(exists=True)`.
- **Mutual exclusivity:** `--task-file` and the individual field options (`--title`, `--task-type`, `--entrypoint`, `--observable`, `--evidence`, `--steps`) are mutually exclusive. If `--task-file` is provided, none of the individual options may be provided. If any individual option is provided, `--task-file` must not be provided.
- **JSON format:** A single task object (not an array), using the same shape as elements in the `--tasks` array:

```json
{
  "title": "Task name",
  "task_type": "OUTCOME",
  "entrypoint": "`./run-test.sh`",
  "observable": "Tests pass",
  "evidence": "`./run-test.sh`",
  "steps": [
    "Write the integration test",
    "Implement the event publisher"
  ]
}
```

- **Required fields in JSON:** All six fields (`title`, `task_type`, `entrypoint`, `observable`, `evidence`, `steps`) must be present in the JSON file. Missing fields produce an error.
- **Error messages:**
  - Both `--task-file` and any individual option provided: `"{command_name}: --task-file and individual task options are mutually exclusive"`
  - Neither `--task-file` nor all required individual options provided: `"{command_name}: either --task-file or all individual task options are required"`
  - Missing field in JSON: `"{command_name}: --task-file JSON is missing required field: {field_name}"`
  - Invalid JSON: `"{command_name}: --task-file is not valid JSON: {parse_error}"`

### FR-3: Refactor `replace-thread` to use shared infrastructure

The existing `replace-thread` command defines its options individually rather than using `_thread_spec_options`. After implementing FR-1, refactor `replace-thread` to use the same shared option decorator and resolution logic as `insert-thread-before` and `insert-thread-after`, eliminating the duplicated option definitions.

## Security Requirements

These are local CLI commands that read and write files on the user's filesystem. No network access, no authentication, no multi-user concerns. The only security-relevant behavior is file path validation, which Click handles via `click.Path(exists=True)`.

## Non-Functional Requirements

- **Backward compatibility:** All existing command invocations with inline options must continue to work identically. No changes to option names, types, or behavior for existing options.
- **Consistency:** Error message format, option naming (`--tasks-file` for thread commands, `--task-file` for task commands), and Click option types must match the established pattern in `replace-thread`.
- **Testability:** Each affected command must have tests covering: file-based input, inline input, both-provided error, neither-provided error.

## Success Metrics

- All 5 affected commands accept file-based input.
- Existing tests continue to pass unchanged.
- New tests cover the file-based input paths and error cases.

## Epics and User Stories

### Epic 1: `--tasks-file` on insert-thread commands

**US-1.1:** As a coding agent, I can use `--tasks-file` with `insert-thread-after` so that I can write task JSON to a temporary file instead of passing it inline.

**US-1.2:** As a coding agent, I can use `--tasks-file` with `insert-thread-before` so that I can write task JSON to a temporary file instead of passing it inline.

**US-1.3:** As a coding agent, I get a clear error message if I provide both `--tasks` and `--tasks-file` on an insert-thread command.

### Epic 2: `--task-file` on single-task commands

**US-2.1:** As a coding agent, I can use `--task-file` with `insert-task-after` so that I can define the entire task in a JSON file instead of passing six individual CLI options.

**US-2.2:** As a coding agent, I can use `--task-file` with `insert-task-before` so that I can define the entire task in a JSON file.

**US-2.3:** As a coding agent, I can use `--task-file` with `replace-task` so that I can define the replacement task in a JSON file.

**US-2.4:** As a coding agent, I get a clear error message if I provide both `--task-file` and individual task options.

### Epic 3: Consistency refactor

**US-3.1:** As a maintainer, the `replace-thread` command uses the same shared option decorator as the insert-thread commands, so there is one place to update thread-creation options.

## Scenarios

These scenarios define the end-to-end behaviors that a steel-thread plan should cover.

### Scenario 1: Insert thread after using `--tasks-file` (primary)

A coding agent writes a JSON array of tasks to a temporary file, then runs:

```
i2code plan insert-thread-after plan.md --after 2 \
  --title "Event Publishing" \
  --introduction "Add event publishing support" \
  --tasks-file /tmp/tasks.json \
  --rationale "Added event publishing thread"
```

The plan file is updated with a new thread 3 containing the tasks from the file.

### Scenario 2: Insert task after using `--task-file`

A coding agent writes a single task JSON object to a file, then runs:

```
i2code plan insert-task-after plan.md --thread 1 --after 2 \
  --task-file /tmp/task.json \
  --rationale "Added integration test task"
```

The plan file is updated with a new task 1.3 containing the definition from the file.

### Scenario 3: Replace task using `--task-file`

A coding agent writes an updated task definition to a file, then runs:

```
i2code plan replace-task plan.md --thread 1 --task 2 \
  --task-file /tmp/task.json \
  --rationale "Updated task with corrected steps"
```

Task 1.2 is replaced with the content from the file.

### Scenario 4: Error — both file and inline provided

A coding agent accidentally provides both `--tasks` and `--tasks-file`:

```
i2code plan insert-thread-after plan.md --after 2 \
  --title "Test" --introduction "Test" \
  --tasks '[...]' --tasks-file /tmp/tasks.json \
  --rationale "test"
```

The command exits with code 1 and prints: `"insert-thread-after: --tasks and --tasks-file are mutually exclusive"` to stderr.

### Scenario 5: Error — missing required field in task file

A coding agent provides a `--task-file` that omits the `evidence` field:

```json
{
  "title": "My Task",
  "task_type": "OUTCOME",
  "entrypoint": "`./run.sh`",
  "observable": "It works",
  "steps": ["Do the thing"]
}
```

The command exits with code 1 and prints: `"{command_name}: --task-file JSON is missing required field: evidence"` to stderr.

### Scenario 6: Backward compatibility — inline options still work

All existing command invocations with inline `--tasks` (thread commands) or individual field options (task commands) continue to work identically with no changes required by callers.
