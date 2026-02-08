Migrate the plan-file-management scripts into `i2c`, a UV-installable Python CLI tool.

Currently, plan management commands are invoked as:

    uv run skills/plan-file-management/scripts/plan-manager.py <subcommand> <plan_file> [options]

The target invocation is:

    i2c plan <subcommand> <plan_file> [options]

Where `i2c` is installed via `uv tool install` and available on the PATH.

## Tool Design

- **Package**: `src/i2c/` at the repo root with `pyproject.toml` defining `[project.scripts] i2c = "i2c.cli:main"`
- **CLI framework**: Click (nested command groups)
- **Dependencies**: Click only; no other external dependencies
- **Command groups**: `plan` is the first subcommand group; others are planned for later

## Package Structure

```
pyproject.toml
src/
  i2c/
    __init__.py
    cli.py                     # Top-level Click group
    plan/
      __init__.py
      cli.py                   # Plan subgroup: Click commands and handlers
      _helpers.py              # Shared: append_change_history, atomic_write, _extract_thread_sections, etc.
      fix_numbering.py         # Pure function: fix_numbering(plan) -> str
      mark_task_complete.py    # Pure function: mark_task_complete(plan, ...) -> str
      mark_task_incomplete.py
      mark_step_complete.py
      mark_step_incomplete.py
      get_next_task.py
      get_thread.py
      get_summary.py
      list_threads.py
      insert_thread_before.py
      insert_thread_after.py
      delete_thread.py
      replace_thread.py
      reorder_threads.py
      insert_task_before.py
      insert_task_after.py
      delete_task.py
      replace_task.py
      reorder_tasks.py
      move_task_before.py
      move_task_after.py
```

## Design Decisions

- **One module per command**: Each pure function lives in its own module. CLI handlers and Click wiring live separately in `plan/cli.py`.
- **Shared helpers**: `append_change_history`, `atomic_write`, `_extract_thread_sections`, `_parse_task_block`, `_serialize_thread`, `_serialize_task`, `_find_task_boundaries` go in `plan/_helpers.py`.
- **Tests import pure functions directly**: `from i2c.plan.fix_numbering import fix_numbering`
- **Delete old files**: Remove `skills/plan-file-management/scripts/plan-manager.py` after migration. Update `skills/plan-file-management/SKILL.md` to reference `i2c plan ...`.
