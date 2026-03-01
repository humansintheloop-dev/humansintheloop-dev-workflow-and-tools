# Platform Capability Specification: Migrate Plan Manager to UV-Installable `i2c` CLI

## Purpose and Context

Migrate the plan-file-management scripts from a monolithic, single-file argparse CLI into `i2c`, a properly packaged, UV-installable Python CLI tool using Click.

### Current State

- **Script**: `skills/plan-file-management/scripts/plan-manager.py` (1,761 lines)
- **Architecture**: Single file, argparse-based, 28 pure functions, 20 command handlers, 23 subcommands
- **Dependencies**: Zero external (pure stdlib: `argparse`, `os`, `re`, `sys`, `tempfile`, `datetime`)
- **Invocation**: `uv run skills/plan-file-management/scripts/plan-manager.py <subcommand> <plan_file> [options]`
- **PEP 723 metadata**: `requires-python = ">=3.10"`, `dependencies = []`
- **Legacy duplicate**: `skills/plan-file-management/scripts/fix-plan-numbering.py` (69 lines)

### Target State

- **Package**: `src/i2c/` with `pyproject.toml` at repo root
- **CLI framework**: Click (nested command groups)
- **Invocation**: `i2c plan <subcommand> <plan_file> [options]`
- **Installation**: `uv tool install .` (globally) or auto-resolved via `uv run` (development)
- **Dependencies**: Click only

## Consumers

| Consumer | How it uses plan-manager | Impact of migration |
|---|---|---|
| **SKILL.md** (`plan-file-management`) | Documents CLI invocation patterns for Claude Code skills | Update all invocation examples to `i2c plan ...` |
| **AGENTS.md** | References script path and test runner | Update path and test runner command |
| **Test suite** (23 files in `tests/plan-manager/`) | Imports pure functions via `importlib.import_module` workaround | Rewrite imports to `from i2c.plan.{plans,tasks,threads} import <fn>` |
| **End-to-end test** (`test-scripts/test-end-to-end.sh`) | Runs pytest via `uv run --python 3.12 --with pytest` | Update test runner command |
| **Claude Code sessions** | Invoke plan-manager via `uv run` as documented in SKILL.md | Will use `i2c plan ...` after migration |

## Capabilities and Behaviors

The `i2c plan` command group must provide all 23 subcommands with identical behavior to the current implementation. No behavioral changes are in scope.

### Read Operations (4 subcommands)

These print output to stdout and do not modify the plan file.

| Subcommand | Arguments | Output format |
|---|---|---|
| `get-next-task` | `PLAN_FILE` | Structured text: thread/task info, metadata fields, numbered steps |
| `list-threads` | `PLAN_FILE` | One line per thread: `Thread N: Title (X/Y tasks completed)` |
| `get-summary` | `PLAN_FILE` | Key-value lines: plan name, idea type, overview, thread/task counts |
| `get-thread` | `PLAN_FILE --thread N` | Thread header, introduction, then each task with metadata and steps |

### Task-Level Write Operations (8 subcommands)

These modify the plan file atomically (temp file + rename) and print a confirmation message.

| Subcommand | Required arguments | Optional | Behavior |
|---|---|---|---|
| `mark-task-complete` | `PLAN_FILE --thread N --task M` | `--rationale` | Mark task + all steps `[x]`. Errors if not found or already complete. |
| `mark-task-incomplete` | `PLAN_FILE --thread N --task M` | `--rationale` | Mark task + all steps `[ ]`. Errors if not found or already incomplete. |
| `insert-task-before` | `PLAN_FILE --thread N --before M --title T --task-type TYPE --entrypoint E --observable O --evidence V --steps JSON --rationale R` | | Insert task, auto-renumber. |
| `insert-task-after` | `PLAN_FILE --thread N --after M --title T --task-type TYPE --entrypoint E --observable O --evidence V --steps JSON --rationale R` | | Insert task, auto-renumber. |
| `delete-task` | `PLAN_FILE --thread N --task M --rationale R` | | Remove task, auto-renumber. |
| `replace-task` | `PLAN_FILE --thread N --task M --title T --task-type TYPE --entrypoint E --observable O --evidence V --steps JSON --rationale R` | | Replace in-place, auto-renumber. |
| `reorder-tasks` | `PLAN_FILE --thread N --order CSV --rationale R` | | Reorder tasks within thread. `--order` is comma-separated task numbers. |
| `move-task-before` | `PLAN_FILE --thread N --task M --before P --rationale R` | | Move task M before task P, auto-renumber. |
| `move-task-after` | `PLAN_FILE --thread N --task M --after P --rationale R` | | Move task M after task P, auto-renumber. |

### Step-Level Write Operations (2 subcommands)

| Subcommand | Required arguments | Behavior |
|---|---|---|
| `mark-step-complete` | `PLAN_FILE --thread N --task M --step S --rationale R` | Mark step `[x]`. Errors if not found or already complete. |
| `mark-step-incomplete` | `PLAN_FILE --thread N --task M --step S --rationale R` | Mark step `[ ]`. Errors if not found or already incomplete. |

### Thread-Level Write Operations (5 subcommands)

| Subcommand | Required arguments | Behavior |
|---|---|---|
| `insert-thread-before` | `PLAN_FILE --before N --title T --introduction I --tasks JSON --rationale R` | Insert thread, auto-renumber. |
| `insert-thread-after` | `PLAN_FILE --after N --title T --introduction I --tasks JSON --rationale R` | Insert thread, auto-renumber. |
| `delete-thread` | `PLAN_FILE --thread N --rationale R` | Remove thread, auto-renumber. |
| `replace-thread` | `PLAN_FILE --thread N --title T --introduction I --tasks JSON --rationale R` | Replace in-place, auto-renumber. |
| `reorder-threads` | `PLAN_FILE --order CSV --rationale R` | Reorder all threads. `--order` is comma-separated thread numbers. |

### Utility Operations (1 subcommand)

| Subcommand | Arguments | Behavior |
|---|---|---|
| `fix-numbering` | `PLAN_FILE` | Renumber all threads and tasks sequentially. |

## High-Level APIs, Contracts, and Integration Points

### Package Structure

```
pyproject.toml
src/
  i2c/
    __init__.py
    cli.py                     # Top-level Click group: @click.group() main
    plan/
      __init__.py
      cli.py                   # Plan subgroup: registers commands from handler modules
      plan_cli.py         # Handlers: get-next-task, list-threads, get-summary, get-thread, fix-numbering
      task_cli.py         # Handlers: mark-task-*, insert-task-*, delete-task, replace-task, reorder-tasks, move-task-*, mark-step-*
      thread_cli.py       # Handlers: insert-thread-*, delete-thread, replace-thread, reorder-threads
      _helpers.py              # Shared internal functions
      plans.py                 # Pure functions: fix_numbering, get_next_task, get_summary, get_thread, list_threads
      tasks.py                 # Pure functions: mark_task_*, insert_task_*, delete_task, replace_task, reorder_tasks, move_task_*, mark_step_*
      threads.py               # Pure functions: insert_thread_*, delete_thread, replace_thread, reorder_threads
```

### pyproject.toml Contract

```toml
[project]
name = "i2c"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["click"]

[project.scripts]
i2c = "i2c.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/i2c"]
```

### Module Contract: Pure Functions

Pure functions are organized into three modules by scope. Each function has the same signature as the current implementation. Functions are pure: they accept a plan string and return a modified plan string (or a dict for read operations).

#### `plans.py` — Plan-Level Pure Functions (5 functions)

| Public function | Signature |
|---|---|
| `fix_numbering` | `(plan: str) -> str` |
| `get_next_task` | `(plan: str) -> dict \| None` |
| `get_thread` | `(plan: str, thread_number: int) -> dict` |
| `get_summary` | `(plan: str) -> dict` |
| `list_threads` | `(plan: str) -> list[dict]` |

#### `tasks.py` — Task + Step Pure Functions (11 functions)

| Public function | Signature |
|---|---|
| `mark_task_complete` | `(plan: str, thread_number: int, task_number: int, rationale: str \| None = None) -> str` |
| `mark_task_incomplete` | `(plan: str, thread_number: int, task_number: int, rationale: str \| None = None) -> str` |
| `mark_step_complete` | `(plan: str, thread_number: int, task_number: int, step_number: int, rationale: str) -> str` |
| `mark_step_incomplete` | `(plan: str, thread_number: int, task_number: int, step_number: int, rationale: str) -> str` |
| `insert_task_before` | `(plan: str, thread_number: int, before_task: int, title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str], rationale: str) -> str` |
| `insert_task_after` | `(plan: str, thread_number: int, after_task: int, title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str], rationale: str) -> str` |
| `delete_task` | `(plan: str, thread_number: int, task_number: int, rationale: str) -> str` |
| `replace_task` | `(plan: str, thread_number: int, task_number: int, title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str], rationale: str) -> str` |
| `reorder_tasks` | `(plan: str, thread_number: int, task_order: list[int], rationale: str) -> str` |
| `move_task_before` | `(plan: str, thread_number: int, task_number: int, before_task: int, rationale: str) -> str` |
| `move_task_after` | `(plan: str, thread_number: int, task_number: int, after_task: int, rationale: str) -> str` |

#### `threads.py` — Thread Pure Functions (5 functions)

| Public function | Signature |
|---|---|
| `insert_thread_before` | `(plan: str, before_thread: int, title: str, introduction: str, tasks: list[dict], rationale: str) -> str` |
| `insert_thread_after` | `(plan: str, after_thread: int, title: str, introduction: str, tasks: list[dict], rationale: str) -> str` |
| `delete_thread` | `(plan: str, thread_number: int, rationale: str) -> str` |
| `replace_thread` | `(plan: str, thread_number: int, title: str, introduction: str, tasks: list[dict], rationale: str) -> str` |
| `reorder_threads` | `(plan: str, thread_order: list[int], rationale: str) -> str` |

### Module Contract: `_helpers.py`

Shared internal functions used by multiple operation modules:

| Function | Signature | Used by |
|---|---|---|
| `atomic_write` | `(file_path: str, content: str) -> None` | All write command handlers in `plan/cli.py` |
| `append_change_history` | `(plan: str, operation: str, rationale: str) -> str` | Most write operations |
| `_extract_thread_sections` | `(plan: str) -> tuple[str, list[tuple[int, str]], str]` | Thread-level operations, `list_threads`, `get_summary`, `get_thread` |
| `_parse_task_block` | `(lines: list[str], start: int, end: int, thread_num: int) -> dict` | `get_next_task`, `get_thread` |
| `_serialize_thread` | `(title: str, introduction: str, tasks: list[dict]) -> str` | `insert_thread_before/after`, `replace_thread` |
| `_serialize_task` | `(title: str, task_type: str, entrypoint: str, observable: str, evidence: str, steps: list[str]) -> str` | `insert_task_before/after`, `replace_task` |
| `_find_task_boundaries` | `(lines: list[str], thread_number: int) -> list[tuple[int, int, int]]` | Task insert/delete/replace/reorder/move operations |

### Module Contract: `plan/cli.py` (Plan Command Group)

This module defines the `@click.group()` named `plan` and registers all commands from the three handler modules:

```python
import click
from i2c.plan.plan_cli import register as register_plan_commands
from i2c.plan.task_cli import register as register_task_commands
from i2c.plan.thread_cli import register as register_thread_commands

@click.group()
def plan():
    """Plan file management commands."""
    pass

register_plan_commands(plan)
register_task_commands(plan)
register_thread_commands(plan)
```

### Module Contract: Command Handler Files

Each handler file defines Click commands and exposes a `register(group)` function that adds them to the plan group.

All command handlers own:
- File I/O (read plan file, call `atomic_write` for writes)
- JSON parsing of `--steps` and `--tasks` arguments
- Error handling: catch `ValueError` from pure functions, print to stderr, exit code 1
- Confirmation messages to stdout

#### `plan_cli.py` — Plan-Level Reads + Utility (5 commands)

| Command | Pure function import |
|---|---|
| `get-next-task` | `from i2c.plan.plans import get_next_task` |
| `list-threads` | `from i2c.plan.plans import list_threads` |
| `get-summary` | `from i2c.plan.plans import get_summary` |
| `get-thread` | `from i2c.plan.plans import get_thread` |
| `fix-numbering` | `from i2c.plan.plans import fix_numbering` |

#### `task_cli.py` — Task + Step Mutations (11 commands)

| Command | Pure function import |
|---|---|
| `mark-task-complete` | `from i2c.plan.tasks import mark_task_complete` |
| `mark-task-incomplete` | `from i2c.plan.tasks import mark_task_incomplete` |
| `insert-task-before` | `from i2c.plan.tasks import insert_task_before` |
| `insert-task-after` | `from i2c.plan.tasks import insert_task_after` |
| `delete-task` | `from i2c.plan.tasks import delete_task` |
| `replace-task` | `from i2c.plan.tasks import replace_task` |
| `reorder-tasks` | `from i2c.plan.tasks import reorder_tasks` |
| `move-task-before` | `from i2c.plan.tasks import move_task_before` |
| `move-task-after` | `from i2c.plan.tasks import move_task_after` |
| `mark-step-complete` | `from i2c.plan.tasks import mark_step_complete` |
| `mark-step-incomplete` | `from i2c.plan.tasks import mark_step_incomplete` |

Step commands are grouped here because they share the `--thread --task` argument pattern and logically operate within task scope.

#### `thread_cli.py` — Thread Mutations (5 commands)

| Command | Pure function import |
|---|---|
| `insert-thread-before` | `from i2c.plan.threads import insert_thread_before` |
| `insert-thread-after` | `from i2c.plan.threads import insert_thread_after` |
| `delete-thread` | `from i2c.plan.threads import delete_thread` |
| `replace-thread` | `from i2c.plan.threads import replace_thread` |
| `reorder-threads` | `from i2c.plan.threads import reorder_threads` |

### Module Contract: `i2c/cli.py` (Top-Level Group)

```python
import click
from i2c.plan.cli import plan

@click.group()
def main():
    """i2c — Idea to Code development workflow tools."""
    pass

main.add_command(plan)
```

### Error Handling Contract

All error behavior must be preserved exactly:

| Error condition | Current behavior | Click equivalent |
|---|---|---|
| Pure function raises `ValueError` | Handler prints message to stderr, exits 1 | Same: catch `ValueError`, `click.echo(str(e), err=True)`, `sys.exit(1)` |
| Invalid JSON in `--steps`/`--tasks` | Handler prints parse error to stderr, exits 1 | Same pattern with `json.JSONDecodeError` |
| Missing required argument | argparse prints usage + error, exits 2 | Click prints usage + error, exits 2 (built-in) |
| No subcommand given | argparse prints help, exits 1 | Click prints help, exits 0 (Click default; acceptable difference) |

### Output Format Contract

All stdout output must match the current format character-for-character (except the no-subcommand help text, which changes with Click).

**Read operations** produce structured text (not JSON):
- `get-next-task`: `Thread N, Task N.M: Title\n  TaskType: ...\n  Entrypoint: ...\n  ...`
- `list-threads`: `Thread N: Title (X/Y tasks completed)` per line
- `get-summary`: `Plan: ...\nIdea Type: ...\nOverview: ...\nThreads: N\nTasks: X/Y completed`
- `get-thread`: Thread header, introduction, then tasks with metadata and steps

**Write operations** produce confirmation text:
- `mark-task-complete`: `Marked task N.M as complete`
- `insert-task-before/after`: `Inserted task 'Title' in thread N`
- `delete-task`: `Deleted task N.M`
- etc.

### Test Import Contract (post-migration)

Tests import pure functions directly from the package:

```python
from i2c.plan.plans import fix_numbering
from i2c.plan.tasks import mark_task_complete
from i2c.plan._helpers import append_change_history
```

No `sys.path` manipulation or `importlib` workaround needed.

### Test Runner Contract (post-migration)

```bash
uv run --with pytest pytest tests/plan-manager/
```

This resolves the local `pyproject.toml` project, making `i2c` importable. No editable install step required.

## Non-Functional Requirements

| Requirement | Target | Rationale |
|---|---|---|
| **Python version** | `>=3.12` | Matches existing e2e test (`--python 3.12`) |
| **External dependencies** | Click only | Minimizes footprint; all business logic uses stdlib only |
| **Atomic writes** | Preserved | Temp file + `os.rename` pattern prevents partial writes |
| **Test coverage** | All 23 existing test files pass | Existing tests are the migration's correctness oracle |
| **Output compatibility** | Character-for-character match on all subcommand outputs | Consumers (SKILL.md, Claude Code sessions) depend on output format |
| **No behavioral changes** | Zero | This is a structural migration only |

## Scenarios and Workflows

### Primary End-to-End Scenario: Install and Use `i2c plan`

1. From the repo root, run `uv tool install .` to install `i2c` globally
2. Run `i2c plan get-summary docs/features/plan-manager-mcp/plan-manager-mcp-plan.md`
3. Verify output matches format: `Plan: ...\nIdea Type: ...\n...`
4. Run `i2c plan mark-task-complete docs/features/plan-manager-mcp/plan-manager-mcp-plan.md --thread 1 --task 1 --rationale "Test"`
5. Verify plan file is modified atomically and confirmation message printed
6. Run `i2c plan fix-numbering docs/features/plan-manager-mcp/plan-manager-mcp-plan.md`
7. Verify numbering is correct

### Scenario: Development Workflow

1. Clone the repo
2. Run `uv run --with pytest pytest tests/plan-manager/` — all 23 test files pass
3. Edit a pure function module (e.g., `src/i2c/plan/plans.py`)
4. Re-run tests — change is picked up without any install step

### Scenario: Extensibility (Future Command Group)

1. Create `src/i2c/newgroup/cli.py` with a `@click.group()` named `newgroup`
2. In `src/i2c/cli.py`, add `from i2c.newgroup.cli import newgroup; main.add_command(newgroup)`
3. `i2c newgroup <subcommand>` is now available
4. No changes needed to `i2c plan` commands

### Scenario: Test Migration Verification

1. For each of the 23 test files, verify the test imports use `from i2c.plan.{plans,tasks,threads} import <fn>`
2. Remove all `sys.path.insert` and `importlib.import_module` workarounds
3. All tests pass with the new import pattern

## Constraints and Assumptions

| Constraint | Detail |
|---|---|
| **No behavioral changes** | Pure function logic is moved as-is. No refactoring of business logic. |
| **Big-bang migration** | All 23 subcommands migrate together. No incremental/dual-mode period. |
| **Delete old files** | After migration: remove `plan-manager.py`, `fix-plan-numbering.py`. |
| **Build system** | Hatchling (standard, minimal configuration). |
| **Click is the only new dependency** | No other libraries introduced. |
| **Argument names preserved** | `--thread`, `--task`, `--step`, `--before`, `--after`, `--order`, `--title`, `--task-type`, `--entrypoint`, `--observable`, `--evidence`, `--steps`, `--tasks`, `--introduction`, `--rationale` — all unchanged. |
| **Positional `plan_file` preserved** | First positional argument to every subcommand. |

### Assumptions

- `uv run` with a local `pyproject.toml` will make the `i2c` package importable for tests without an explicit install step.
- Click's built-in help formatting is an acceptable replacement for argparse's help output.
- The `--task-type` argument maps to Click's `--task-type` option (Click handles hyphens in option names, converting them to underscores in Python: `args.task_type`).

## Files to Create

| File | Purpose |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, entry point |
| `src/i2c/__init__.py` | Package marker |
| `src/i2c/cli.py` | Top-level Click group |
| `src/i2c/plan/__init__.py` | Subpackage marker |
| `src/i2c/plan/cli.py` | Plan command group; registers commands from handler modules |
| `src/i2c/plan/plan_cli.py` | Click handlers: `get-next-task`, `list-threads`, `get-summary`, `get-thread`, `fix-numbering` |
| `src/i2c/plan/task_cli.py` | Click handlers: `mark-task-*`, `insert-task-*`, `delete-task`, `replace-task`, `reorder-tasks`, `move-task-*`, `mark-step-*` |
| `src/i2c/plan/thread_cli.py` | Click handlers: `insert-thread-*`, `delete-thread`, `replace-thread`, `reorder-threads` |
| `src/i2c/plan/_helpers.py` | 7 shared internal functions |
| `src/i2c/plan/plans.py` | Pure functions: `fix_numbering`, `get_next_task`, `get_summary`, `get_thread`, `list_threads` |
| `src/i2c/plan/tasks.py` | Pure functions: `mark_task_complete/incomplete`, `mark_step_complete/incomplete`, `insert/delete/replace/reorder_task*`, `move_task_*` |
| `src/i2c/plan/threads.py` | Pure functions: `insert/delete/replace/reorder_thread*` |

## Files to Modify

| File | Change |
|---|---|
| `skills/plan-file-management/SKILL.md` | Replace all `uv run skills/.../plan-manager.py` with `i2c plan` |
| `AGENTS.md` | Update script path, test runner command |
| `test-scripts/test-end-to-end.sh` | Update test runner invocation |
| `tests/plan-manager/test_*.py` (23 files) | Replace `importlib`/`sys.path` imports with `from i2c.plan.{plans,tasks,threads} import <fn>` |
| `pytest.ini` | Update if test discovery paths change |

## Files to Delete

| File | Reason |
|---|---|
| `skills/plan-file-management/scripts/plan-manager.py` | Replaced by `src/i2c/plan/` |
| `skills/plan-file-management/scripts/fix-plan-numbering.py` | Redundant legacy script |

## Acceptance Criteria

1. **All 23 existing test files pass** with `uv run --with pytest pytest tests/plan-manager/` using the new `from i2c.plan.<module>` imports.
2. **`i2c plan <subcommand>`** is callable after `uv tool install .` and produces identical output to the old script for all 23 subcommands.
3. **Atomic write** behavior is preserved (temp file + `os.rename`).
4. **Error messages** match the current format (e.g., `mark-task-complete: task 1.5 does not exist`).
5. **Exit codes** match: 0 for success, 1 for domain errors, 2 for usage errors.
6. **No `sys.path` or `importlib` hacks** remain in test files.
7. **Old files deleted**: `plan-manager.py` and `fix-plan-numbering.py` are removed.
8. **SKILL.md updated**: All invocation examples reference `i2c plan ...`.
9. **AGENTS.md updated**: References new package structure and test runner.
10. **`pyproject.toml` exists** at repo root with correct metadata, dependencies (`click`), and entry point (`i2c = "i2c.cli:main"`).

## Change History

### 2026-02-09: Split command handlers into scope-based modules

Replaced single `plan/cli.py` (23 handlers) with three handler modules grouped by scope:
- `plan_cli.py` — plan-level reads + utility (5 commands)
- `task_cli.py` — task + step mutations (10 commands)
- `thread_cli.py` — thread mutations (5 commands)

`plan/cli.py` now defines only the Click group and registers commands from the handler modules via `register(group)` functions. Rationale: better organization by domain scope, easier navigation.

### 2026-02-09: Consolidate pure functions into 3 scope-based modules

Replaced 21 individual pure-function files (one per function) with 3 scope-based modules:
- `plans.py` — 5 plan-level functions (`fix_numbering`, `get_next_task`, `get_summary`, `get_thread`, `list_threads`)
- `tasks.py` — 11 task+step functions (`mark_task_*`, `mark_step_*`, `insert/delete/replace/reorder_task*`, `move_task_*`)
- `threads.py` — 5 thread functions (`insert/delete/replace/reorder_thread*`)

Rationale: mirrors the CLI handler split (`plan_cli.py`, `task_cli.py`, `thread_cli.py`), reduces file count from 21 to 3, keeps related functions together.
