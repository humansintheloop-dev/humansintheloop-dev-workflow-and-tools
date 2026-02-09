# Agents

## Running Plan Manager Tests

pytest is NOT installed globally. Always use `uv` to run it:

    uv run --with pytest pytest tests/plan-manager/

Never use bare `pytest` or `python -m pytest`.

## Project Structure

- Plan manager package: `src/i2code/plan/` (installed as `i2code` CLI tool via `pyproject.toml`)
- Tests: `tests/plan-manager/`
- Plan file: `docs/features/plan-manager-mcp/plan-manager-mcp-plan.md`
- CLI invocation: `i2code plan <subcommand> <plan_file> [options]`
- Test imports use `from i2code.plan.<module> import <function>`
