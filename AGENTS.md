# Agents

## Running Plan Manager Tests

pytest is NOT installed globally. Always use `uv` to run it:

    uv run --with pytest pytest tests/plan-manager/

Never use bare `pytest` or `python -m pytest`.

## Project Structure

- Plan manager script: `skills/plan-file-management/scripts/plan-manager.py`
- Tests: `tests/plan-manager/`
- Plan file: `docs/features/plan-manager-mcp/plan-manager-mcp-plan.md`
- The script uses PEP 723 inline metadata with no dependencies beyond stdlib
- Test imports use `importlib.import_module('plan-manager')` due to hyphen in filename
