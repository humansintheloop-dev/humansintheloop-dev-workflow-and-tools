# Test Directory Mirrors Source Package

## Problem

When source modules move to a new package, tests can get left behind in their original directory. This creates a disconnect where the test location no longer reflects what it tests, making navigation harder.

## Structure

| Key Element | Directory | Responsibility |
|-------------|-----------|---------------|
| Source subpackage | `src/i2code/<subpackage>/` | Production code |
| Test directory | `tests/<subpackage>/` | Tests for that subpackage |
| Test file | `tests/<subpackage>/test_<module>.py` | Tests for a specific module |

### Reference implementation

- `src/i2code/idea/resolver.py` → `tests/idea/test_resolver.py`
- `src/i2code/go_cmd/orchestrator.py` → `tests/go-cmd/test_orchestrator*.py`
- `src/i2code/idea_cmd/state_cmd.py` → `tests/idea-cmd/test_idea_state_cli.py`

## When to Apply

- Moving a source module to a new package
- Creating tests for a new module

## Key Principles

- **Source and test move together.** When a module moves to a new package, its test file moves in the same commit.
- **Test directory mirrors source package.** `src/i2code/foo/` → `tests/foo/`.
- **Test file mirrors source module.** `bar.py` → `test_bar.py`.
