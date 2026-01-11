# Project Guidelines

## Executing bash commands

IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

When copying or moving files:
- Avoid compound commands with `&&` - run commands separately
- Avoid wildcard patterns (`*.java`) - copy files individually
- Single-file operations are more reliable with Bash permission system

## Skills

Always invoke the relevant skill before performing these actions:

- **Before creating git commits**: Use the `idea-to-code:commit-guidelines` skill
- **When practicing TDD**: Use the `idea-to-code:tdd` skill
- **When working from a plan file**: Use the `idea-to-code:plan-tracking` skill
- **When creating Dockerfiles**: Use the `idea-to-code:dockerfile-guidelines` skill
- **When moving/renaming files**: Use the `idea-to-code:file-organization` skill
- **When writing multiple similar files**: Use the `idea-to-code:incremental-development` skill

## Code Style

- Prefer intention-revealing method names over comments. If you find yourself writing a comment to explain what code does, extract it into a method whose name conveys the intent.

## Tool Selection

Before running any Bash command, ask: "Is there a specialized tool for this?"

- File search → Glob (NOT find or ls)
- Content search → Grep (NOT grep or rg)
- Read files → Read (NOT cat/head/tail)

The specialized tools are faster, have correct permissions, and provide better output formatting.

## Git Commands

Always run git commands from the project root directory. If you need to operate on the repository, cd to the root directory first rather than using `git -C`. This prevents accidentally committing files outside the project root.

## Filing Issue Reports

When asked to file an issue about a mistake:
1. File the issue report documenting the lesson learned
2. Assess current state - if the work is functional, don't undo it
3. Only "fix" if explicitly asked or if the current state is broken
4. Ask for clarification if unsure whether to continue, undo, or just document
