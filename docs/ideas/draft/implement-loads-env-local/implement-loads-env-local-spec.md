# Platform Capability Specification: implement-loads-env-local

## Purpose and Context

`i2code implement` orchestrates development tasks across three execution modes (trunk, worktree, isolate). Commands it runs — Claude, CI checks, build tools — often need environment variables (API keys, service URLs, tokens) defined in a `.env.local` file at the project root. This file is gitignored, so it exists only in the original checkout, not in worktrees or clones.

Today, environment variable availability is inconsistent:
- **Trunk mode**: `.env.local` is on disk in CWD but not loaded into the process environment.
- **Worktree mode**: `.env.local` is absent (gitignored files aren't copied to worktrees).
- **Isolate mode**: `.env.local` is passed to isolarium via `--env-file`, but not loaded into the host `i2code` process itself.

This capability adds a single `load_dotenv(".env.local")` call early in the `i2code implement` execution path, before mode selection, so that all modes start with a consistent environment.

## Consumers

- `i2code implement` command (all three execution modes)
- Any subprocess spawned by `i2code implement` (Claude, git, build tools, CI scripts) — these inherit the process environment

## Capabilities and Behaviors

### CAP-1: Load `.env.local` from CWD at startup

At the beginning of `ImplementCommand.execute()`, before mode selection or validation, load `.env.local` from the current working directory into `os.environ` using `python-dotenv`.

- **File path**: `.env.local` relative to CWD (no directory traversal, no fallback paths)
- **Override behavior**: `override=False` — existing environment variables take precedence over values in `.env.local`
- **Missing file**: If `.env.local` does not exist in CWD, `load_dotenv()` returns `False` and does nothing. No error, no warning, no log message.
- **File format**: Standard dotenv format as parsed by `python-dotenv` (KEY=value, comments with `#`, variable interpolation with `${VAR}`)

### CAP-2: Add `python-dotenv` dependency

Add `python-dotenv` to the project's dependencies in `pyproject.toml`.

## APIs, Contracts, and Integration Points

### Integration with `ImplementCommand`

The `load_dotenv` call is placed in `ImplementCommand.execute()`, before `_validate_and_apply_defaults()`. This ensures env vars are available to all downstream code regardless of execution mode.

```python
from dotenv import load_dotenv

def execute(self):
    load_dotenv(".env.local")
    self._validate_and_apply_defaults()
    # ... rest of execute
```

### Integration with existing IsolateMode `.env.local` handling

`IsolateMode._find_env_file()` currently looks for `.env.local` in `main_repo_dir` and passes it to isolarium via `--env-file`. This existing behavior is independent and remains unchanged — it serves a different purpose (making `.env.local` available inside the VM). The new `load_dotenv` call makes env vars available to the host process before isolarium is launched.

## Non-Functional Requirements

- **No new CLI options**: This is transparent to the user. No flags, no configuration.
- **No performance impact**: `load_dotenv` reads a small file once at startup.
- **Backwards compatible**: Existing env vars are never overridden. If `.env.local` doesn't exist, behavior is identical to today.

## Scenarios and Workflows

### Primary scenario: Implement with `.env.local` in CWD

1. User has `.env.local` in the project root with `GITHUB_TOKEN=abc123`.
2. User runs `i2code implement some-idea` from the project root.
3. `load_dotenv(".env.local")` loads `GITHUB_TOKEN` into `os.environ`.
4. Subsequent commands (Claude, git, CI tools) inherit `GITHUB_TOKEN`.

### Scenario: `.env.local` does not exist

1. User runs `i2code implement some-idea` from a directory without `.env.local`.
2. `load_dotenv(".env.local")` returns `False`.
3. Execution proceeds normally with whatever env vars are already set.

### Scenario: Env var already set in shell

1. User exports `GITHUB_TOKEN=shell-value` in their shell.
2. `.env.local` contains `GITHUB_TOKEN=file-value`.
3. User runs `i2code implement some-idea`.
4. `GITHUB_TOKEN` remains `shell-value` (no override).

### Scenario: Isolate mode

1. User has `.env.local` in CWD.
2. User runs `i2code implement --isolate some-idea`.
3. `load_dotenv(".env.local")` loads env vars into the host process.
4. `IsolateMode` also passes `.env.local` to isolarium via `--env-file` (existing behavior, unchanged).

## Constraints and Assumptions

- `.env.local` is always gitignored (already the case — listed in `.gitignore`).
- The file name is hardcoded to `.env.local`. No support for `.env`, `.env.production`, or other variants.
- `python-dotenv` is a well-maintained, lightweight library with no transitive dependencies.
- Loading happens once at command startup; there is no hot-reloading.

## Acceptance Criteria

1. When `.env.local` exists in CWD, its variables are present in `os.environ` after `ImplementCommand.execute()` begins, for all three modes.
2. When `.env.local` does not exist in CWD, no error occurs and execution proceeds normally.
3. When an env var is already set in the shell environment, the shell value is preserved (not overridden by `.env.local`).
4. `python-dotenv` is listed as a dependency in `pyproject.toml`.
5. Existing `IsolateMode._find_env_file()` behavior is unchanged.
