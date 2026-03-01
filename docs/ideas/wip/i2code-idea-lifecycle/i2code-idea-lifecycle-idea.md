# i2code idea lifecycle

## Problem

Idea state lives only in the directory structure (`docs/ideas/{draft,ready,wip,completed,abandoned}/`). There's no CLI support for listing ideas by state or moving them between states. The `i2code go` command doesn't prompt the user to advance the state, so ideas stay in `draft/` or `ready/` even after implementation begins.

## Goal

Add `i2code idea` subcommands to list ideas and change their state, integrate state transitions into `i2code go` so the lifecycle advances with user confirmation, and allow `go` and `idea` commands to accept idea names (not just directory paths).

## Desired Behavior

### `idea list`

- `i2code idea list` — flat alphabetical table of all ideas: name, state, directory (similar to `git worktree list`)
- `i2code idea list --state wip` — filter to a single state, same columnar format
- Shell completions for `--state` values

### `idea state`

- `i2code idea state <name>` — show the current state of an idea
- `i2code idea state <name> <new-state>` — move an idea to a new state via `git mv` + commit
- Enforced transition rules:
  - `draft → ready` — requires plan file
  - `ready → wip` — requires plan file
  - `wip → completed` — allowed
  - `any → abandoned` — always allowed
  - Backward moves or skipping states — require `--force`
- `--force` bypasses both transition ordering and artifact validation
- Shell completions for idea name and target state

### `go` integration

- `i2code go` accepts either a directory path or an idea name (resolved across all state directories)
- Shell completions for both paths and idea names
- When idea is in `draft/` and has a plan file: prompt "Move idea to ready?"
- Before calling implement when idea is in `ready/`: prompt "Move idea to wip?"
- If user declines either prompt, continue the workflow silently
- After a move, update the internal `IdeaProject` to the new path
- `go` does NOT handle end-of-lifecycle transitions (`completed`, `abandoned`)

### Idea name resolver

- Reusable module (not coupled to `go` or `idea_cmd`) so other commands can adopt it later
- Scans `{git-root}/docs/ideas/{state}/<name>/` across all state directories
- If a name resolves to multiple states, that's an error (an idea should exist in exactly one state)

## Locations

- **Resolver** — `src/i2code/idea_resolver.py` (new, shared module)
- **Idea commands** — `src/i2code/idea_cmd/` (add `list` and `state` subcommands)
- **Go integration** — `src/i2code/go_cmd/orchestrator.py` (name resolution, state transition prompts)
- **CLI registration** — `src/i2code/cli.py`
