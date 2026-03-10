# Idea: Maintain Idea State in Metadata File

## Problem

Idea lifecycle state is currently encoded in the filesystem path (`docs/ideas/{state}/{name}/`). State transitions require `git mv` to move the entire directory, which creates noisy git history and makes it harder to trace an idea's history.

## Proposed Change

Replace directory-based state tracking with a metadata file (`<idea-name>-metadata.yaml`) inside each idea directory. The metadata file initially contains only the lifecycle `state` field (draft, ready, wip, completed, abandoned). Additional fields can be added incrementally.

### Directory structure

Collapse the 5 state directories into 2:

- `docs/ideas/active/` — all ideas that haven't been explicitly archived (regardless of lifecycle state)
- `docs/ideas/archived/` — ideas explicitly archived by the user

### State transitions

- `i2code idea state <name> <new-state>` edits the `state` field in the metadata file (no directory move)
- Auto-commits by default; `--no-commit` flag to skip
- Existing transition rules (forward-only, plan-file requirements, `--force` override) remain unchanged

### Archival

- `i2code idea archive <name>` — moves idea from `active/` to `archived/` via `git mv`
- `i2code idea unarchive <name>` — moves idea back to `active/`
- Archival is orthogonal to lifecycle state (an idea retains its state when archived)

### Migration

- `i2code idea migrate` — permanent CLI subcommand that migrates all ideas from the old directory-based structure to the new metadata-based structure in one commit
- All existing ideas go to `active/`, with metadata files generated from their current directory location

### Listing

- `i2code idea list` shows active ideas only by default
- `--archived` or `--all` flags to include archived ideas
- `--state` filter continues to work, reading state from metadata files

### Out of scope

- Merging metadata file with existing `*-wt-state.json` (kept separate — different concerns)
- Rich metadata beyond `state` (can be added later)
