# Platform Capability Specification: Plan File Management Scripts

## Purpose and Context

The Plan File Management Scripts provide Claude with structured, programmatic access to manipulate steel-thread implementation plan files. Plan files are central to the idea-to-code workflow -- they define the sequence of steel threads and tasks that guide implementation. Today, Claude modifies plan files via raw text editing, which is error-prone: numbering gets out of sync, checkbox syntax can be misformatted, and structural edits (inserting/deleting threads) require careful markdown manipulation.

The scripts expose plan file operations as CLI subcommands with structured inputs and outputs, making plan manipulation reliable and auditable. Every structural mutation is automatically renumbered, and every write operation records a rationale in a change history section within the plan file itself.

The scripts are part of the `plan-file-management` skill (`skills/plan-file-management/SKILL.md`), implemented as a single Python script (`skills/plan-file-management/scripts/plan-manager.py`) using PEP 723 inline script metadata (no dependencies beyond stdlib), run via `uv run`.

---

## Consumers

| Consumer | Usage |
|---|---|
| **Claude Code (via skill)** | Primary consumer. The `plan-file-management` skill's `SKILL.md` tells Claude when and how to invoke `uv run plan-manager.py <subcommand>` to read and manipulate plan files during plan creation, execution, and refinement. |
| **`implement_with_worktree.py`** | Existing workflow script. Does not call the plan manager directly (no shared code), but operates on the same plan files. The `fix-numbering` subcommand can correct plan files after the workflow script or other processes edit them. |
| **Human developers** | Indirect consumers. Benefit from consistently formatted plan files and the change history audit trail. May trigger fix-numbering via Claude after manual edits. |

---

## Plan File Data Model

The scripts parse and manipulate markdown plan files with the following structure, derived from the canonical example at `docs/features/wt-pr-based-development/wt-pr-based-development-plan.md`.

### Top-Level Sections

```markdown
# Implementation Plan: <plan-name>

## Idea Type
**<classification>** - <description>

---

## Overview
<free-text overview of the plan>

---

## Steel Thread <N>: <Title>
<introduction paragraph>

- [ ] **Task <N>.<M>: <task-title>**
  - TaskType: <INFRA|OUTCOME>
  - Entrypoint: `<command>`
  - Observable: <what can be observed>
  - Evidence: `<verification command>`
  - Steps:
    - [ ] <step description>
    - [ ] <step description>

---

## Summary
<free-text summary>

---

## Change History
### <YYYY-MM-DD HH:MM> - <operation>
<rationale>
```

### Entities

**Thread**: A steel thread (numbered section) containing an introduction and one or more tasks.

| Field | Type | Description |
|---|---|---|
| `number` | integer | Thread number (1-based, auto-assigned) |
| `title` | string | Thread title (text after `Steel Thread N: `) |
| `introduction` | string | Free-text paragraph(s) below the heading |
| `tasks` | list[Task] | Ordered list of tasks |

**Task**: A work item within a thread.

| Field | Type | Description |
|---|---|---|
| `number` | integer | Task number within thread (1-based, auto-assigned) |
| `title` | string | Task title (text within `**Task N.M: ...**`) |
| `completed` | boolean | `true` if `[x]`, `false` if `[ ]` |
| `task_type` | string | `INFRA` or `OUTCOME` |
| `entrypoint` | string | Command to run the task |
| `observable` | string | What can be observed when the task succeeds |
| `evidence` | string | Verification command |
| `steps` | list[Step] | Ordered list of implementation steps |

**Step**: An implementation step within a task.

| Field | Type | Description |
|---|---|---|
| `description` | string | Step description text |
| `completed` | boolean | `true` if `[x]`, `false` if `[ ]` |

---

## Capabilities and Behaviors

All operations are subcommands of `skills/plan-file-management/scripts/plan-manager.py`, invoked as:

```
uv run skills/plan-file-management/scripts/plan-manager.py <subcommand> <plan_file> [options]
```

### Read Operations

Read operations print their output to stdout as human-readable text.

#### `list-threads`

Returns all threads with their numbers, titles, and completion status.

```
uv run plan-manager.py list-threads <plan_file>
```

**Output**: List of thread summaries, each containing:
- `number`: thread number
- `title`: thread title
- `total_tasks`: total number of tasks
- `completed_tasks`: number of completed tasks

#### `get-thread`

Returns a specific thread's full content.

```
uv run plan-manager.py get-thread <plan_file> --thread <thread_number>
```

**Output**: Full thread data including introduction, all tasks with their metadata, and all steps.

**Error**: Exits with error if `thread_number` does not exist.

#### `get-next-task`

Returns the first uncompleted task across the entire plan.

```
uv run plan-manager.py get-next-task <plan_file>
```

**Output**: The first task where `completed` is `false`, including its thread number, task number, full metadata, and steps. Prints a message indicating all tasks are complete if none remain.

#### `get-summary`

Returns the plan's overview, idea type, and overall progress.

```
uv run plan-manager.py get-summary <plan_file>
```

**Output**:
- `plan_name`: from the `# Implementation Plan:` heading
- `idea_type`: from the `## Idea Type` section
- `overview`: from the `## Overview` section
- `total_threads`: count of threads
- `total_tasks`: count of all tasks
- `completed_tasks`: count of completed tasks

### Write Operations

All write operations that modify plan structure accept a `--rationale` option. The rationale is appended to a `## Change History` section at the end of the plan file, timestamped with the current date and time. Fix-numbering does not require a rationale (it is a mechanical correction).

Structural mutations (insert/delete thread, insert/delete task) automatically renumber all threads and tasks after the modification.

Write operations modify the plan file in place (using atomic writes).

#### `fix-numbering`

Renumbers all threads and tasks sequentially. Intended for use after arbitrary edits made outside the script.

```
uv run plan-manager.py fix-numbering <plan_file>
```

**Behavior**: Renumbers all `## Steel Thread N:` headings and all `**Task N.M:**` references sequentially starting from 1.

#### `insert-thread-before`

Inserts a fully structured thread before the specified thread.

```
uv run plan-manager.py insert-thread-before <plan_file> --before <thread_number> --title <title> --introduction <introduction> --tasks <tasks_json> --rationale <rationale>
```

| Option | Type | Required | Description |
|---|---|---|---|
| `--before` | integer | yes | Thread number to insert before |
| `--title` | string | yes | Thread title |
| `--introduction` | string | yes | Thread introduction text |
| `--tasks` | JSON string | yes | Complete task definitions (see Task input schema below) |
| `--rationale` | string | yes | Reason for the insertion |

**Behavior**: Inserts the thread, then auto-renumbers all threads and tasks. Appends rationale to change history.

**Error**: Exits with error if `before` thread does not exist.

#### `insert-thread-after`

Inserts a fully structured thread after the specified thread. Same options as `insert-thread-before` except `--before` is replaced with `--after`.

#### `delete-thread`

Removes a thread entirely.

```
uv run plan-manager.py delete-thread <plan_file> --thread <thread_number> --rationale <rationale>
```

**Behavior**: Removes the thread and all its tasks. Auto-renumbers remaining threads and tasks. Appends rationale to change history.

**Error**: Exits with error if `thread_number` does not exist.

#### `replace-thread`

Replaces a thread's entire content with a new definition.

```
uv run plan-manager.py replace-thread <plan_file> --thread <thread_number> --title <title> --introduction <introduction> --tasks <tasks_json> --rationale <rationale>
```

**Behavior**: Replaces the thread content in place (same position). Auto-renumbers. Appends rationale to change history.

**Error**: Exits with error if `thread_number` does not exist.

#### `reorder-threads`

Reorders threads according to a specified ordering.

```
uv run plan-manager.py reorder-threads <plan_file> --order <comma_separated_thread_numbers> --rationale <rationale>
```

| Option | Type | Required | Description |
|---|---|---|---|
| `--order` | comma-separated integers | yes | Current thread numbers listed in desired new order (e.g., `3,1,2`) |
| `--rationale` | string | yes | Reason for the reordering |

**Behavior**: Rearranges threads to match the specified order, then auto-renumbers all threads and tasks sequentially starting from 1. Appends rationale to change history.

**Error**: Exits with error if `--order` does not contain exactly the set of existing thread numbers (no duplicates, no missing threads, no invalid numbers).

#### `insert-task-before`

Inserts a task before a specified task within a thread.

```
uv run plan-manager.py insert-task-before <plan_file> --thread <thread_number> --before <task_number> --title <title> --task-type <INFRA|OUTCOME> --entrypoint <command> --observable <text> --evidence <command> --steps <steps_json> --rationale <rationale>
```

**Behavior**: Inserts the task, then auto-renumbers all tasks within the thread. Appends rationale to change history.

**Error**: Exits with error if `thread_number` or `task_number` does not exist.

#### `insert-task-after`

Inserts a task after a specified task within a thread. Same options as `insert-task-before` except `--before` is replaced with `--after`.

#### `delete-task`

Removes a task from a thread.

```
uv run plan-manager.py delete-task <plan_file> --thread <thread_number> --task <task_number> --rationale <rationale>
```

**Behavior**: Removes the task. Auto-renumbers remaining tasks. Appends rationale to change history.

**Error**: Exits with error if `thread_number` or `task_number` does not exist.

#### `mark-task-complete`

Marks a task and all its steps as complete.

```
uv run plan-manager.py mark-task-complete <plan_file> --thread <thread_number> --task <task_number> --rationale <rationale>
```

**Behavior**: Changes `- [ ]` to `- [x]` on the task line and all its step lines. Appends rationale to change history.

**Error**: Exits with error if task does not exist or is already complete.

#### `mark-step-complete`

Marks a single step as complete.

```
uv run plan-manager.py mark-step-complete <plan_file> --thread <thread_number> --task <task_number> --step <step_number> --rationale <rationale>
```

**Behavior**: Changes `- [ ]` to `- [x]` on the specific step line. Appends rationale to change history.

**Error**: Exits with error if step does not exist or is already complete.

### Task Input Schema

When providing tasks to insert/replace operations via `--tasks`, the JSON has the following structure:

```json
[
  {
    "title": "Task title",
    "task_type": "INFRA",
    "entrypoint": "command to run",
    "observable": "what can be observed",
    "evidence": "verification command",
    "steps": ["step 1 description", "step 2 description"]
  }
]
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | string | yes | Task title |
| `task_type` | string | yes | `INFRA` or `OUTCOME` |
| `entrypoint` | string | yes | Command to run |
| `observable` | string | yes | Observable outcome |
| `evidence` | string | yes | Verification command |
| `steps` | list[string] | yes | Step descriptions (all uncompleted) |

---

## Integration Points

### Skill Registration

The script is integrated via the `plan-file-management` skill definition at `skills/plan-file-management/SKILL.md`. The skill tells Claude when to invoke the script and provides usage instructions. Claude invokes the script directly using `uv run`:

```
uv run skills/plan-file-management/scripts/plan-manager.py <subcommand> <plan_file> [options]
```

### File Location

The script lives at `skills/plan-file-management/scripts/plan-manager.py` within the plugin directory. The script uses PEP 723 inline metadata to declare its requirements:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
```

No external dependencies are required -- the script uses only the Python standard library.

---

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Operation latency** | Each subcommand should complete within 1 second for plan files up to 1000 lines |
| **File safety** | Write operations must be atomic -- write to a temp file, then rename -- to prevent corruption on interruption |
| **Idempotency** | Mark-complete on an already-complete task/step returns an error (not a silent no-op), preventing accidental double-marking |
| **File encoding** | All plan files are UTF-8 |
| **Concurrency** | Single-writer assumed. The script does not need to handle concurrent writes to the same plan file. |
| **Error reporting** | All errors include the subcommand name, the parameter that caused the failure, and a human-readable message. Errors exit with a non-zero exit code. |
| **No dependencies** | The script must have no dependencies beyond the Python standard library |

---

## Scenarios and Workflows

### Primary End-to-End Scenario: Claude Executes a Plan Task and Updates Progress

1. Claude receives instruction to work on the next plan task.
2. Claude runs `uv run plan-manager.py get-next-task path/to/plan.md`.
3. Script parses the plan, prints Task 3.2 with full metadata (title, entrypoint, observable, evidence, steps).
4. Claude implements the task, working through each step.
5. After completing step 1, Claude runs `uv run plan-manager.py mark-step-complete path/to/plan.md --thread 3 --task 2 --step 1 --rationale "Implemented helper function"`.
6. Script updates `- [ ]` to `- [x]` for step 1, appends to change history.
7. Claude completes remaining steps similarly.
8. Claude runs `uv run plan-manager.py mark-task-complete path/to/plan.md --thread 3 --task 2 --rationale "All steps verified, tests passing"`.
9. Script marks the task and any remaining unchecked steps as complete, appends to change history.
10. Claude runs `uv run plan-manager.py get-next-task path/to/plan.md` to proceed to the next task.

### Scenario: Claude Inserts a New Thread During Plan Refinement

1. Claude is refining a plan and determines a new thread is needed between threads 4 and 5.
2. Claude runs `uv run plan-manager.py insert-thread-after path/to/plan.md --after 4 --title "Error Recovery" --introduction "Handles error scenarios..." --tasks '[...]' --rationale "Added error recovery thread after discovering unhandled edge cases in thread 4"`.
3. Script inserts the new thread, auto-renumbers (old thread 5 becomes thread 6, etc.), and appends to change history.
4. Claude runs `uv run plan-manager.py list-threads path/to/plan.md` to verify the updated structure.

### Scenario: Claude Deletes an Obsolete Task

1. During implementation, Claude determines Task 5.3 is no longer needed.
2. Claude runs `uv run plan-manager.py delete-task path/to/plan.md --thread 5 --task 3 --rationale "Covered by task 5.2 after refactoring"`.
3. Script removes the task, renumbers remaining tasks in thread 5, and appends to change history.

### Scenario: Fix Numbering After Manual Edits

1. A developer manually edits the plan file (e.g., copy-pasting a thread from another plan).
2. The numbering is now inconsistent.
3. Claude runs `uv run plan-manager.py fix-numbering path/to/plan.md`.
4. Script renumbers all threads and tasks sequentially.

### Scenario: Replace Thread with Updated Definition

1. Claude needs to restructure thread 3 significantly.
2. Claude runs `uv run plan-manager.py get-thread path/to/plan.md --thread 3` to get the current content.
3. Claude constructs the revised thread definition.
4. Claude runs `uv run plan-manager.py replace-thread path/to/plan.md --thread 3 --title "..." --introduction "..." --tasks '[...]' --rationale "Restructured to separate concerns between API and persistence"`.
5. Script replaces the thread in place, auto-renumbers task numbers, and appends to change history.

### Scenario: Reorder Threads During Plan Refinement

1. Claude is refining a plan and determines the thread ordering should change to reflect revised priorities.
2. Claude runs `uv run plan-manager.py list-threads path/to/plan.md` to see the current thread structure.
3. Claude runs `uv run plan-manager.py reorder-threads path/to/plan.md --order 3,1,2,4,5 --rationale "Moved infrastructure thread to front to unblock other work"`.
4. Script rearranges threads to match the specified order, auto-renumbers all threads and tasks (old thread 3 becomes thread 1, old thread 1 becomes thread 2, etc.), and appends to change history.
5. Claude runs `uv run plan-manager.py list-threads path/to/plan.md` to verify the updated structure.

### Scenario: Get Plan Summary for Status Report

1. Claude is asked for a progress update.
2. Claude runs `uv run plan-manager.py get-summary path/to/plan.md`.
3. Script prints: plan name, idea type, overview text, 17 total threads, 34 total tasks, 12 completed tasks.
4. Claude reports: "12 of 34 tasks complete across 17 steel threads."

---

## Constraints and Assumptions

- **`uv` must be installed** on the host machine. The script is launched via `uv run`, which handles Python version resolution.
- **Single plan file per operation**. Each subcommand specifies the plan file path. The script does not maintain state between invocations.
- **No shared code** with `implement_with_worktree.py`. The plan manager has its own independent plan file parser.
- **Plan file format is fixed**. The script expects the markdown structure described in the Data Model section. It does not handle arbitrary markdown files.
- **No external dependencies**. The script uses only the Python standard library.
- **Change history section** is appended at the end of the plan file. If the section does not exist, it is created on the first write operation.
- **Thread and task numbers are 1-based** and always sequential after any mutation.

---

## Acceptance Criteria

1. **All 4 read subcommands** print structured data to stdout that accurately reflects the plan file content.
2. **All 11 write subcommands** correctly modify the plan file and the resulting file is valid markdown that matches the expected plan format.
3. **Auto-renumbering** produces correct sequential numbering after every structural mutation (insert/delete thread or task).
4. **Fix-numbering** corrects inconsistent numbering introduced by external edits.
5. **Change history** is appended for every write operation that accepts a rationale, with timestamp and operation name.
6. **Atomic writes** prevent file corruption -- a crash mid-operation never leaves a partially written plan file.
7. **Error handling** returns clear, actionable messages for invalid inputs (nonexistent thread/task numbers, already-complete tasks, missing required parameters) and exits with a non-zero exit code.
8. **Skill integration** -- the script runs correctly when invoked via `uv run` and the `SKILL.md` provides Claude with accurate usage instructions.
9. **Round-trip fidelity** -- reading a plan file and writing it back without modifications produces an identical file (no formatting drift).
10. **Performance** -- operations complete within 1 second for plan files up to 1000 lines.
