# Spec: Restructure Unit Tests by Module

## Scope

Reorganize `tests/implement/` unit test files. No production code changes.

## Rules

1. Each `test_<module>.py` tests only classes/functions from `src/i2code/implement/<module>.py`
2. Delete duplicate tests rather than moving them
3. Move tests verbatim — no rewrites during the move
4. Run tests after each step

## Files to Delete

| File | Reason |
|---|---|
| `test_dry_run.py` | All 4 tests duplicated by `test_implement_command.py` |
| `test_state_management.py` | All 5 tests duplicated by `test_workflow_state.py` |
| `test_github_pr.py` | Kitchen sink — split into module files |
| `test_claude_invocation.py` | Kitchen sink — split into module files |
| `test_git_infrastructure.py` | Merge into `test_git_repository_setup.py` |
| `test_idea_validation.py` | Rename to `test_git_setup.py` |

## Files to Create

| File | Production Module |
|---|---|
| `test_pr_helpers.py` | `pr_helpers.py` |
| `test_branch_lifecycle.py` | `branch_lifecycle.py` |
| `test_git_repository_setup.py` | `git_repository.py` (setup/infra concern) |
| `test_git_setup.py` | `git_setup.py` (renamed from `test_idea_validation.py`) |

## Net Change

- ~30 duplicate tests eliminated
- ~50 tests moved to correct module files
- 6 files deleted, 4 files created
