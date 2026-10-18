# Project Guidelines

IMPORTANT: Before exploring the codebase, read [CODEBASE.md](CODEBASE.md) first. Use it as the navigation guide to locate packages, tests, skills, and feature docs.

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
- **When implementing or refactoring code**: Use the `idea-to-code:apply-design-patterns` skill
- **When investigating CI build failures**: Use the `idea-to-code:debugging-ci-failures` skill
- **When creating or updating GitHub Actions CI workflows**: Use the `idea-to-code:github-workflow-gradle-template` skill
- **When running tests in Java/Gradle projects**: Use the `idea-to-code:test-runner-java-gradle` skill
- **When writing test scripts involving infrastructure**: Use the `idea-to-code:testing-scripts-and-infrastructure` skill
- **When resolving merge or rebase conflicts**: Use the `idea-to-code:git-conflict-resolution` skill
- **When stuck on a problem**: Use the `idea-to-code:ask-a-friend` skill
- **When finding where code is defined or used**: Use the `idea-to-code:find-usage` skill
- **When running commands with verbose output**: Use the `idea-to-code:test-output-to-logfile` skill
- **When documenting a design pattern**: Use the `idea-to-code:write-design-pattern` skill
- **When capturing an idea from a discussion**: Use the `idea-to-code:write-idea` skill

## Code Health

Before committing code changes, read and follow [CODE_SCENE.md](CODE_SCENE.md) for Code Health safeguard and refactoring instructions.

## Referencing Code Locations

- Use `path/to/file:line_number` when referencing a specific line (e.g., `src/i2code/plan/manager.py:42`).
- Use `path/to/file` when referencing a file without a specific line.
- Both formats enable click-to-navigate in the terminal.
- IMPORTANT: This applies to ALL file types: source code, log files, config files and test output. Write `logs/test-implement-nono.log:74`, never "Line 74:", "lines 188-189" or "on line 231".

## Referencing Plan Steps

IMPORTANT: Always name a plan step with its task, e.g. "Task 9.1, Step 4", never a bare "step 4". This applies in messages, commit messages and action items.

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

IMPORTANT: Never use `git commit --amend` unless the user literally says "amend". Make follow-up fixes as new commits. Amending rewrites history and forces a force-push.

## Pre-Commit Checklist

- Run `uvx pyright --level error src/` and fix all type errors before committing.
- Run the CodeScene `pre_commit_code_health_safeguard` BEFORE `git commit`, not after, as [CODE_SCENE.md](CODE_SCENE.md) requires. If quality gates fail, refactor before committing.
- Target a Code Health score of 10.0 for both new and modified files. Don't settle for 9.x.

## Working With the User

- Wait for the user's direction. Don't make changes you weren't asked to make, don't revert changes on your own, and don't presume the next step.
- Never modify permission or security configuration (`settings.json`, `settings.local.json`, sandbox profiles) without asking first. When a failure is caused by a missing permission, report which permission is needed and let the user decide.
- Never record anything in Claude's auto-memory except a handoff to the next session. Put rules and knowledge in this file or in a skill.

## Evidence Before Conclusions

IMPORTANT: Never present an inference as a fact.

- Before stating a root cause, verify it with direct evidence: read the actual file, check the actual environment, read the source code.
- When debugging containers, VMs or remote environments, inspect the state in that environment (e.g. `docker exec`). Never assume host-side state matches.
- When reading logs, check the ordering carefully before concluding which command produced which output.
- State exactly what the evidence shows, and say "I don't know" for gaps. If you are inferring, label it as inference.
- When the user shares log output or error messages, grep for the exact strings first, read the file that produced them, and only then analyze. Never relay an agent's summary as fact without checking it against the code.

## Outside-In TDD

Start from the external interface and work inward, letting failing tests reveal which dependencies to build.

1. Write a failing acceptance test from the caller's perspective, with real inputs (e.g. write a plan to a temp file, parse it, call the method).
2. Stub the missing classes and functions with `raise NotImplementedError`, so pytest collects the test and it fails at execution rather than with a collection error.
3. Write ONE unit test for the outermost layer, for the simplest case, and make it pass with the minimum implementation.
4. When the next unit test needs a dependency that doesn't exist, don't implement it inline. Switch the SUT to the dependency, write ONE unit test for it, and implement the minimum to pass.
5. Return to the outer layer, then run the acceptance tests to find the next gap. Repeat until the acceptance test is green.

Rules:
- Write ONE test at a time, not a batch.
- Never implement a dependency without its own failing test first.
- In the RED phase, run without `-x`, to confirm every test that should fail does fail.
- When tests patch dependencies with `@patch`, assert the mock was called (`assert_called`, `assert_called_once`). Don't rely on indirect evidence.

## Pruning Acceptance Tests After TDD

After outside-in TDD, remove an acceptance test only when all three are true:
1. A unit test makes the same assertion.
2. The unit test is closer to the SUT, constructing the object directly rather than going through parsing.
3. The acceptance test exercises no boundary the unit test skips, such as parser → domain → output.

Keep acceptance tests that exercise end-to-end paths through several layers: parsing a file then calling a method, formatting output via `print()`, or interactions across several entities. Remove those that only re-check a single property, a `None` return or list contents that a unit test already covers.

Process: list each acceptance test with its unit test counterpart (with `path/to/file:line_number` references), remove the redundant ones and any fixtures that become unused, then run the full test suite.

## Pattern-Based Fixes

When fixing issues caused by naming conventions or patterns:
1. Search the entire codebase for similar occurrences before making any changes
2. Fix ALL instances in a single commit
3. Never commit partial fixes for pattern-based problems


<!-- claude-config-files-sha: f8e6469fd91735ffcae2dc46f979cfb0677ec5b6 -->
