# Claude Code Features Used by i2code

This document catalogs the Claude Code features that the i2code toolchain uses.
Each section covers one feature, explains how i2code uses it, and lists the key files involved.

## Plugin System

i2code is packaged as a Claude Code plugin called **idea-to-code**.
A marketplace file at the repository root registers the plugin so Claude Code discovers it automatically.

| File | Purpose |
|---|---|
| `.claude-plugin/marketplace.json` | Root-level marketplace that references the idea-to-code plugin |
| `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json` | Plugin manifest defining skills, commands, and hooks |

## Skills

Skills are reusable prompt fragments that Claude loads on demand via the `Skill` tool.
The plugin registers 19 skills, each defined by a `SKILL.md` file.
The `CLAUDE.md` project instructions tell Claude which skill to invoke for each type of task.

| Skill | When to invoke |
|---|---|
| `apply-design-patterns` | Before implementing or refactoring code |
| `ask-a-friend` | When stuck on a problem |
| `commit-guidelines` | Before creating git commits |
| `debugging-ci-failures` | When investigating CI build failures |
| `dockerfile-guidelines` | When creating Dockerfiles |
| `file-organization` | When moving or renaming files |
| `find-usage` | When finding where code is defined or used |
| `git-conflict-resolution` | When resolving merge or rebase conflicts |
| `github-actions-gradle-cache` | When configuring Gradle caching in GitHub Actions |
| `github-workflow-gradle-template` | When creating GitHub Actions CI workflows |
| `incremental-development` | When writing multiple similar files |
| `plan-file-management` | When renumbering or editing plan file structure |
| `plan-tracking` | When working from a plan file |
| `tdd` | When practicing Test-Driven Development |
| `test-output-to-logfile` | When running commands with verbose output |
| `test-runner-java-gradle` | When running tests in Java/Gradle projects |
| `testing-scripts-and-infrastructure` | When writing test scripts involving infrastructure |
| `write-design-pattern` | When documenting a design pattern |
| `write-idea` | When capturing an idea from a discussion |

All skills live under `claude-code-plugins/idea-to-code/skills/<name>/SKILL.md`.

## Custom Slash Commands

Custom commands are markdown prompts that users invoke via `/idea-to-code:<command>`.
The plugin registers five commands.

| Command | Purpose |
|---|---|
| `claude-issue-report` | Capture a mistake or improvement opportunity with 5-whys analysis |
| `commit-changes` | Stage all changes, review, and commit |
| `commit-staged-changes` | Review staged changes and commit |
| `precommit-check` | Run `./gradlew precommitCheck` |
| `review-design-doc` | Walk through design decisions interactively |

All commands live under `claude-code-plugins/idea-to-code/commands/<name>.md`.

## Hooks

Hooks are scripts that Claude Code executes at specific lifecycle events.
The plugin registers hooks on five events: `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `PermissionRequest`, and `Stop`.

### enforce-bash-conventions.js (PreToolUse)

Blocks Bash commands that violate project conventions. Returns exit code 2 with a corrective message when a rule fires.

**Rules enforced:**

| Pattern blocked | Corrective guidance |
|---|---|
| `git -C <dir>` | cd to root and run git from there |
| `cd <dir> && git ...` | Run git from the project root |
| `git commit` with heredoc | Use `git commit -m "..."` |
| `python -m pytest` | Use `uv run python -m pytest` |
| Bare `pytest` | Use `uv run python -m pytest` |
| `bash script.sh` / `sh script.sh` on executable scripts | Run directly: `./script.sh` |
| `gradlew ... \| tail` | Run gradlew directly; test results are in XML files |
| `pytest ... \| ...` | Use the `test-output-to-logfile` skill instead |

Each blocked command is also appended as a `**Blocked:**` entry to the current session file in `.hitl/sessions/` (see session-recorder below).

Source: `claude-code-plugins/idea-to-code/hooks/enforce-bash-conventions.js`

### session-recorder.js (UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, Stop)

Records Claude Code interactions to markdown files in `.hitl/sessions/`.
Creates a session file per Claude session (`session-YYYY-MM-DD-HHMMSS-<id>.md`) and appends:

- User prompts (on `UserPromptSubmit`)
- Tool calls (on `PreToolUse` and `PostToolUse`)
- Permission requests (on `PermissionRequest`)
- Claude's final response text, extracted from the transcript file (on `Stop`)
- Git commit SHAs when `git commit` succeeds (on `PostToolUse`)

Source: `claude-code-plugins/idea-to-code/hooks/session-recorder.js`

### issue-session-tagger.js (PostToolUse)

Watches for `Write` operations to `.hitl/issues/active/*.md` files and automatically fills in the `claude_session_id` field with the current session ID.

Source: `claude-code-plugins/idea-to-code/hooks/issue-session-tagger.js`

## CLAUDE.md Project Instructions

CLAUDE.md files provide persistent instructions that Claude Code loads into every conversation.
i2code uses two CLAUDE.md files:

| File | Purpose |
|---|---|
| `CLAUDE.md` | Root-level project guidelines: bash conventions, required skill invocations, code style, tool selection, git rules |
| `src/i2code/config_files/CLAUDE.md` | Template copied into target projects by `i2code setup claude-files` (`src/i2code/setup_cmd/claude_files.py`) |

Both files direct Claude to invoke specific skills for specific task types, prefer dedicated tools over shell equivalents, and follow project-specific git conventions.

## Permissions Configuration (settings.local.json)

Claude Code uses `.claude/settings.local.json` to pre-authorize or deny tool invocations without prompting the user.
i2code defines a comprehensive permissions file and programmatically manages permissions for worktrees.

### Static permissions

The template at `src/i2code/config_files/settings.local.json` pre-authorizes:

- **Build tools:** `./gradlew`, `go build`, `go test`, `npm test`
- **Git operations:** `git add`, `git commit`, `git diff`, `git log`, `git status`, etc.
- **Python tooling:** `uv run`, `uvx ruff check`, `uvx pyright`, `uvx vulture`
- **Docker:** `docker ps`, `docker logs`, `docker inspect`, `docker info`, `docker exec`, `docker build`, `docker compose ps/logs/config/build`
- **All plugin skills:** `Skill(idea-to-code:*)`
- **CodeScene MCP tools:** `code_health_review`, `pre_commit_code_health_safeguard`, `code_health_auto_refactor`, `code_health_score`

Denied: `docker compose down`, `docker compose up`, `docker rm`

### Programmatic permission management

The `i2code.claude.permissions` module (`src/i2code/claude/permissions.py`) provides:

- `build_allowed_tools_flag()` — builds `--allowedTools` values scoping Read to the repo and Edit to the idea directory
- `build_read_only_tools_flag()` — builds `--allowedTools` granting only Read access
- `calculate_claude_permissions()` — computes the full permission list for a repo root
- `ensure_claude_permissions()` — creates or updates `.claude/settings.local.json` in a worktree or clone
- `setup_claude_settings_local_json()` — copies the source project's settings and ensures required permissions

Path-scoped file permissions must use `Edit(<path>)`, never `Write(<path>)`. Claude Code's file
permission checks only match `Edit` rules, and an `Edit(<path>)` rule covers all file-editing tools
(Write included). A path-scoped `Write` rule is rejected with a warning at startup. The bare
`Write` tool name (no path) remains valid.

## CLI Invocation Modes

i2code invokes the `claude` CLI programmatically in two modes:

### Interactive mode

Inherits the terminal so Claude's TUI is visible. Used for tasks where the developer is present.

```
claude [--resume <id>] <prompt>
```

### Non-interactive (batch) mode

Captures output as stream-json for progress monitoring and error extraction.

```
claude --verbose --output-format=stream-json -p <prompt>
```

In batch mode, i2code prints a progress dot per JSON message and parses the final `result` message for:
- Permission denials (tool name and input)
- Error messages
- Last N messages for diagnostics

Key files:
| File | Purpose |
|---|---|
| `src/i2code/implement/claude_runner.py` | `ClaudeRunner.execute(ClaudeCodeCommand)` — builds the argv (`_build_argv`) and dispatches to `_run_claude_interactive()` or `_run_claude_with_output_capture()` (stream-json parsing) |
| `src/i2code/implement/command_builder.py` | Assembles Claude commands for 7 task types (task execution, scaffolding, CI fix, triage, fix feedback, recovery, address feedback) |

### Capturing the result text

For summary reports, i2code runs batch mode with `--allowedTools Read`, takes the `result` message's text from the stream-json output (`ClaudeResult.result_text`), and writes it to the report file itself — Claude Code has no output-file flag.

Source: `src/i2code/improve/summary_reports.py`

## --add-dir Flag

`--add-dir <directory>` grants Claude tool access to a directory outside the working directory. `ClaudeCodeCommand.add_dirs` is rendered as one `--add-dir` per directory by `ClaudeRunner._build_argv`.

| Context | Added directories |
|---|---|
| Summary reports | The project directory |
| Session analysis | `.hitl/sessions/` and `.hitl/issues/` |
| Task execution | Any `--add-dir` values passed through `extra_cli_args` (split out by `CommandBuilder._split_extra_cli_args`) |

Sources: `src/i2code/implement/claude_runner.py`, `src/i2code/implement/command_builder.py`, `src/i2code/improve/summary_reports.py`, `src/i2code/improve/analyze_sessions.py`

## --allowedTools Flag

i2code uses the `--allowedTools` CLI flag to scope Claude's capabilities per invocation:

| Context | Allowed tools |
|---|---|
| Task execution (non-interactive) | Full permission list from `calculate_claude_permissions()` |
| Scaffolding (non-interactive) | `Write,Read,Edit,Bash(gradle --version),Bash(mkdir -p:*)` |
| Plan creation | `Read(/<repo>/**)` only |
| Plan revision | `Read(/<repo>/**),Edit(/<idea>/**)` |
| Spec creation / revision | `Read(/<repo>/**),Edit(/<idea>/**)` |
| Brainstorm | `Read(/<repo>/**),Edit(/<idea>/**)` |
| Summary reports | `Read` only |
| Session analysis | `Read,Edit,Write` |

Sources: `src/i2code/claude/permissions.py`, `src/i2code/implement/command_builder.py`, `src/i2code/implement/worktree_mode.py`, `src/i2code/implement/trunk_mode.py`, `src/i2code/go_cmd/create_plan.py`, `src/i2code/go_cmd/revise_plan.py`, `src/i2code/spec_cmd/create_spec.py`, `src/i2code/spec_cmd/revise_spec.py`, `src/i2code/idea_cmd/brainstorm.py`, `src/i2code/improve/summary_reports.py`, `src/i2code/improve/analyze_sessions.py`

## Session Management (--resume, --session-id)

i2code uses Claude Code sessions to maintain conversational context across multiple invocations for the same idea (e.g., brainstorm, then spec, then design, then plan).

- `--resume <id>` resumes an existing session
- `--session-id <id>` starts a new session with a specific ID

Session IDs are persisted in the idea directory as a file.
The `session_manager` module reads or creates session IDs and builds the appropriate CLI args.

Source: `src/i2code/session_manager.py`

## @ File References in Prompts

Prompt templates use the `@path` syntax to tell Claude Code to read files into context:

```
* Idea: @{{ idea_directory }}/*-idea.*
* Specification: @{{ idea_directory }}/*-spec.md
* Implementation tasks: @{{ idea_directory }}/*-plan.md
```

This avoids explicit Read tool calls by having Claude Code expand the file references before the conversation begins.

Sources: `src/i2code/implement/templates/task_execution.j2`, `src/i2code/implement/templates/scaffolding.j2`

## Git Worktrees

i2code creates git worktrees for isolated implementation of ideas, so work-in-progress on one idea doesn't affect the main working tree.

- `GitRepository.ensure_worktree()` creates a worktree at `<repo>-wt-<idea>` and returns a new `GitRepository` wrapping it
- `ProjectSetup.setup_worktree()` copies settings and runs setup scripts in the worktree
- Claude Code is then invoked with `cwd` set to the worktree directory

An alternative `clone()` path creates shallow clones at `<repo>-cl-<idea>` for cases where worktrees aren't suitable.

Sources: `src/i2code/implement/git_repository.py`, `src/i2code/implement/worktree_setup.py`

## MCP Server Integration (CodeScene)

The permissions file pre-authorizes four CodeScene MCP tools.
The `CODE_SCENE.md` (referenced from `CLAUDE.md`) instructs Claude to:

1. Run `pre_commit_code_health_safeguard` before every commit
2. Run `code_health_review` if the safeguard reports a regression
3. Use `code_health_auto_refactor` for large/complex functions
4. Use `code_health_score` for quick numeric assessments

Source: `CODE_SCENE.md`, `src/i2code/config_files/settings.local.json`

## Plugin Skill Discovery

The `plugin_skills` module enumerates installed plugin skills by scanning the Claude Code plugin cache directory (`~/.claude/plugins/cache`).
This is used to pass available skill names to prompt templates (e.g., for design document creation).

Source: `src/i2code/go_cmd/plugin_skills.py`

## Prompt Templates

i2code uses Jinja2 templates to construct Claude prompts for different task types:

| Template | Used for |
|---|---|
| `task_execution.j2` | Implementing plan tasks with TDD and plan-tracking |
| `scaffolding.j2` | Initial project setup |
| `ci_fix.j2` | Fixing CI failures |
| `triage_feedback.j2` | Triaging PR review comments |
| `fix_feedback.j2` | Addressing specific PR feedback |
| `commit_recovery.j2` | Committing recovered uncommitted changes |
| `address_feedback.j2` | Handling PR feedback in worktree mode |

Templates live in `src/i2code/implement/templates/`.

Additional prompt templates live in `src/i2code/prompt-templates/` for the earlier workflow stages (`brainstorm-idea`, `create-spec`, `create-design-doc`, `create-implementation-plan`, `revise-plan`, `repair-plan`) and the `improve` commands (`analyze-sessions`, `review-issues`, `create-summary-report`, `update-claude-files-from-project`, `update-project-claude-md`, `update-project-settings`).
