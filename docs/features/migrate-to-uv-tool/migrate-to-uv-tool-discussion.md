# Migrate to UV Tool — Discussion

## Classification

**Category**: C. Platform/infrastructure capability

**Rationale**: This restructures internal developer tooling — migrating a 1,761-line monolithic argparse script into a properly packaged, UV-installable Click CLI — without changing user-facing behavior. It improves developer ergonomics, testability, and extensibility.

## Codebase Analysis (derived, not asked)

- **Current script**: `skills/plan-file-management/scripts/plan-manager.py` (1,761 lines)
- **Architecture**: argparse-based, single file, 28 pure functions, 20 command handlers, 23 subcommands
- **Dependencies**: Zero external (pure stdlib: argparse, os, re, sys, tempfile, datetime)
- **Tests**: 23 test files in `tests/plan-manager/`, using `importlib.import_module` workaround
- **Legacy duplicate**: `fix-plan-numbering.py` (69 lines) — simpler version of `fix_numbering`
- **No existing**: `pyproject.toml`, `src/` directory, Click usage, or `i2c` package

## Questions & Answers

### Q1: Development/test workflow after migration

**Question**: After migration, tests will `from i2c.plan.fix_numbering import fix_numbering`, requiring the package to be importable. How should the dev/test workflow work?

- A. **Editable install** — `uv pip install -e .` then `pytest tests/`
- B. **`uv run` with project** — `uv run --with pytest pytest tests/` auto-resolves local pyproject.toml
- C. **No preference** — pick simplest option

**Answer**: B — `uv run` with project. `uv run --with pytest pytest tests/` auto-resolves the local `pyproject.toml`, no explicit install step needed. Closest to the current workflow.

## Derived Decisions (no question needed)

| Decision | Value | Rationale |
|---|---|---|
| Python version | `>=3.12` | e2e test already pins `--python 3.12` |
| Output format | Preserve exactly | SKILL.md consumers depend on current JSON (read ops) and plain text (write ops) output |
| Legacy `fix-plan-numbering.py` | Delete alongside `plan-manager.py` | Subset of `fix_numbering`; redundant after migration |
| `AGENTS.md` | Update references | Points to old script path and test runner command |
| Migration approach | Big-bang | Codebase is small (1,761 lines), tests comprehensive (23 files); incremental adds complexity without benefit |
| Argument names | Preserve current names | `--thread`, `--task`, `--rationale`, etc. — SKILL.md compatibility |
| Future `i2c` command groups | Don't over-design | Top-level Click group is inherently extensible; `plan` is the only concrete group now |
| `pytest.ini` | Keep and update if needed | Already exists with markers; test discovery path may need adjustment |
