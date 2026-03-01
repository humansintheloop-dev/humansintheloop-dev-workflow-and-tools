# Codebase Guide

## Package Layout

| Directory | Purpose |
|-----------|---------|
| `src/i2code/cli.py` | Top-level Click CLI group, registers all subcommands |
| `src/i2code/plan/` | `i2code plan` subcommands (plan file management) |
| `src/i2code/plan_domain/` | Domain model for plan files (Thread, Task, Plan) |
| `src/i2code/implement/` | `i2code implement` subcommand |
| `src/i2code/tracking/` | `i2code manage-tracking` command (HITL tracking setup) |
| `src/i2code/idea_cmd/` | `i2code idea` subcommand |
| `src/i2code/design_cmd/` | `i2code design` subcommand |
| `src/i2code/spec_cmd/` | `i2code spec` subcommand |
| `src/i2code/setup_cmd/` | `i2code setup` subcommand |
| `src/i2code/improve/` | `i2code improve` subcommand |
| `src/i2code/scripts/` | Shell scripts invoked by CLI commands |
| `src/i2code/templates/` | Prompt templates |

## Test Layout

| Directory | Tests for |
|-----------|-----------|
| `tests/plan-manager/` | `src/i2code/plan/` CLI integration tests |
| `tests/plan-domain/` | `src/i2code/plan_domain/` domain model tests |
| `tests/implement/` | `src/i2code/implement/` tests |
| `tests/tracking/` | `src/i2code/tracking/` tests |
| `tests/script-command/` | `src/i2code/script_command.py` tests |
| `tests/script-runner/` | `src/i2code/script_runner.py` tests |
| `tests/templates/` | `src/i2code/templates/` tests |
| `test-scripts/` | End-to-end and smoke test shell scripts |

## Skill Sources

Skills are Claude Code slash commands. Source lives in `skills/`, each with a `SKILL.md` file.

| Skill name | Source directory |
|------------|----------------|
| `plan-file-management` | `skills/plan-file-management/` |
| `plan-tracking` | `skills/plan-tracking/` |
| `tdd` | `skills/tdd/` |
| `commit-guidelines` | `skills/commit-guidelines/` |
| `incremental-development` | `skills/incremental-development/` |
| `file-organization` | `skills/file-organization/` |
| `dockerfile-guidelines` | `skills/dockerfile-guidelines/` |
| `debugging-ci-failures` | `skills/debugging-ci-failures/` |
| `testing-scripts-and-infrastructure` | `skills/testing-scripts-and-infrastructure/` |
| `test-runner-java-gradle` | `skills/test-runner-java-gradle/` |
| `ask-a-friend` | `skills/ask-a-friend/` |
| `find-usage` | `skills/find-usage/` |
| `write-idea` | `skills/write-idea/` |
| `github-workflow-gradle-template` | `skills/github-workflow-gradle-template/` |

## Feature Documentation

Feature ideas, specs, and plans live in `docs/ideas/{state}/<feature-name>/` with files:
- `*-idea.md` — the original idea
- `*-spec.md` — specification
- `*-plan.md` — implementation plan

| State | Meaning |
|-------|---------|
| `draft/` | Initial state — idea just captured |
| `ready/` | Has a plan and is ready for implementation |
| `wip/` | Implementation in progress |
| `completed/` | Work is considered done |
| `abandoned/` | Decided to be a bad idea |

## Claude Code Plugin

The project is packaged as a Claude Code plugin in `.claude-plugin/`.

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest: registers skills, slash commands, and hooks |
| `.claude-plugin/marketplace.json` | Marketplace metadata for plugin distribution |

The plugin bundles:
- **Skills** — referenced from `skills/` (see Skill Sources above)
- **Slash commands** — defined in `.claude-plugin/commands/` (e.g., `commit-changes.md`, `precommit-check.md`)
- **Hooks** — JS scripts in `.claude-plugin/hooks/` (session recording, issue tagging, git safety)

## Key Config Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code project instructions |
| `CODEBASE.md` | This file — codebase navigation guide |
| `CODE_SCENE.md` | CodeScene Code Health safeguard rules |
| `pyproject.toml` | Python project config, CLI entry points |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest |
| `.github/workflows/ci.yml` | CI pipeline |
