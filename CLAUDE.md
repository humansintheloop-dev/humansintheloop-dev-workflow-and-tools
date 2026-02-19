# Project Guidelines

## Executing bash commands

IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

When running scripts:
- Run scripts directly: `./script.sh` (NOT `bash ./script.sh`)
- Do not append `2>&1` to redirect stderr
- Do not use `git -C directory` - cd to the top-level directory and run git commands from there

When copying or moving files:
- Avoid compound commands with `&&` - run commands separately
- Avoid wildcard patterns (`*.java`) - copy files individually
- Single-file operations are more reliable with Bash permission system

## Skills

IMPORTANT: Always invoke the relevant skill before performing these actions:

- **Before creating git commits**: Use the `idea-to-code:commit-guidelines` skill
- **When practicing TDD**: Use the `idea-to-code:tdd` skill
- **When working from a plan file**: Use the `idea-to-code:plan-tracking` skill
- **When renumbering or editing plan file structure**: Use the `idea-to-code:plan-file-management` skill
- **When creating Dockerfiles**: Use the `idea-to-code:dockerfile-guidelines` skill
- **When moving/renaming files**: Use the `idea-to-code:file-organization` skill
- **When writing multiple similar files**: Use the `idea-to-code:incremental-development` skill

## Code Health

Before committing code changes, read and follow [CODE_SCENE.md](CODE_SCENE.md) for Code Health safeguard and refactoring instructions.

## Referencing Code Locations

- Use `path/to/file:line_number` when referencing a specific line (e.g., `src/i2code/plan/manager.py:42`).
- Use `path/to/file` when referencing a file without a specific line.
- Both formats enable click-to-navigate in the terminal.

## Code Style

- Prefer intention-revealing method names over comments. If you find yourself writing a comment to explain what code does, extract it into a method whose name conveys the intent.

## Tool Selection

IMPORTANT: Before running any Bash command, ask: "Is there a specialized tool for this?"

- File search → Glob (NOT find or ls)
- Content search → Grep (NOT grep or rg)
- Read files → Read (NOT cat/head/tail)

The specialized tools are faster, have correct permissions, and provide better output formatting.

## Git Commands

IMPORTANT: Always run git commands from the project root directory. If you need to operate on the repository, cd to the root directory first rather than using `git -C`. This prevents accidentally committing files outside the project root.

## Pattern-Based Fixes

When fixing issues caused by naming conventions or patterns:
1. Search the entire codebase for similar occurrences before making any changes
2. Fix ALL instances in a single commit
3. Never commit partial fixes for pattern-based problems

## Running Plan Manager Tests

pytest is NOT installed globally. Always use `uv` to run it:

    uv run --with pytest pytest tests/plan-manager/

Never use bare `pytest` or `python -m pytest`.

## Project Structure

- Plan manager package: `src/i2code/plan/` (installed as `i2code` CLI tool via `pyproject.toml`)
- Implement package: `src/i2code/implement/` (subcommand `i2code implement <idea-directory>`)
- Plan manager tests: `tests/plan-manager/`
- Implement tests: `tests/implement/`
- Plan file: `docs/features/plan-manager-mcp/plan-manager-mcp-plan.md`
- CLI invocation: `i2code plan <subcommand> <plan_file> [options]`
- CLI invocation: `i2code implement <idea-directory> [options]`
- Test imports use `from i2code.plan.<module> import <function>`
- Test imports use `from i2code.implement.<module> import <function>`

<!-- claude-config-files-sha: f8e6469fd91735ffcae2dc46f979cfb0677ec5b6 -->
