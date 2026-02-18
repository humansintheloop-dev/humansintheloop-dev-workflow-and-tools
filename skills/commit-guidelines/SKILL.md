---
name: commit-guidelines
description: Provides a pre-commit checklist and commit message formatting standards for this project. Claude should use this skill when creating git commits to ensure messages follow project conventions, including proper co-authorship attribution and concise formatting.
---

# Pre-Commit Checklist

Before committing, complete these steps in order:

1. Run `uvx ruff check --fix` to auto-fix lint issues. Resolve any unfixable errors.
2. If the `pre_commit_code_health_safeguard` CodeScene MCP tool is available, run it. If Code Health regresses, refactor before committing. CodeScene may flag pre-existing Complex Method smells in files you modified. Fix these before committing (boy scout rule). If `pre_commit_code_health_safeguard` fails with "Not inside a supported VCS root" (common in git worktrees), use `code_health_review` on each modified source file instead. If Code Health regresses, refactor before committing.
3. Run `git add` and `git commit` as separate tool calls (not chained with `&&`).

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
