---
name: commit-guidelines
description: Provides a pre-commit checklist and commit message formatting standards for this project. Claude should use this skill when creating git commits to ensure messages follow project conventions, including proper co-authorship attribution and concise formatting.
---

# Pre-Commit Checklist

Before committing, complete these steps in order:

1. On the final task of a Steel Thread, check for dead code and review findings.
2. If the project has a configured linter, run it with auto-fix. Resolve any unfixable errors.
3. If any new or modified shell scripts will be committed, run `shellcheck` on them and fix any issues.
4. If the `pre_commit_code_health_safeguard` CodeScene MCP tool is available, run it.
   * If it fails with "Not inside a supported VCS root" (common in git worktrees), use `code_health_review` on each modified source file instead.
   * **STOP if quality gates fail.** Do NOT commit until resolved. Do NOT dismiss findings as "pre-existing".
   * If Code Health regresses, refactor the flagged function before committing (boy scout rule).
   * Try to achieve a score of 10 for new code.
   * Try to achieve a score of at least 9.5 for modified files.
5. If adding or modifying production code and coverage tooling is available, verify test coverage and check that new/modified lines are covered.

NOTES:
- **Python dead code (step 1):** `uvx vulture src`
- **Python linter (step 2):** `uvx ruff check --fix`
- **Shell script linting (step 3):** `uvx --from shellcheck-py shellcheck <file.sh>` on each new or modified `.sh` file
- **Python coverage (step 5):** `uv run --with pytest --with pytest-mock --with pytest-cov pytest -m "unit or integration" --cov=src/i2code --cov-report=term-missing`

# Running `git add` and `git commit`

Run `git add` and `git commit` as separate tool calls (not chained with `&&`).

# Commit Message Guidelines

**IMPORTANT**: Always invoke this skill (`idea-to-code:commit-guidelines`) before creating any git commit in projects that use it. This ensures commit messages follow project conventions.

When writing commit messages for this project, follow these guidelines:

## Message Structure

- The commit message should be concise and descriptive of the changes made
- The first line of the commit message should describe the high-level goal of the change
- If the work is associated with an issue, include the issue number in the commit message


## Co-authorship Attribution

Use "Co-authored by Claude Code" in the commit message instead of the standard Claude Code attribution format.

Specifically, use:
```
Co-authored by Claude Code
```

Instead of:
```
🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Special Cases

### Converting Classes to Records

When converting classes to records, use a concise commit message that simply says which classes were converted. No need to explain method renames or justification.

Example:
```
Convert UserProfile and AccountSettings classes to records

Co-authored by Claude Code
```
