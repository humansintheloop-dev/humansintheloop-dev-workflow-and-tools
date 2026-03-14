# Discussion: Maintain Idea State in Metadata File

## Context

The current system manages idea lifecycle state via directory location (`docs/ideas/{state}/{name}/`). There are 5 state directories: `draft`, `ready`, `wip`, `completed`, `abandoned`. State transitions use `git mv` to move the entire idea directory, which creates noisy git history and complicates tracing.

The proposal is to:
1. Store state in a metadata file (e.g., `*-metadata.yaml`) within each idea directory.
2. Collapse from 5 state directories to 2: `active/` and `archived/`.

### Codebase impact analysis

Components that would need to change:
- `src/i2code/idea/resolver.py` — `resolve_idea()`, `list_ideas()`, `state_from_path()` all derive state from the directory path
- `src/i2code/idea_cmd/state_cmd.py` — state transitions use `git mv`
- `src/i2code/idea_cmd/transition_rules.py` — validation logic (unchanged in rules, but invocation context changes)
- `src/i2code/implement/idea_project.py` — `IdeaProject` derives paths from directory; would need new `metadata_file` property
- `src/i2code/idea_cmd/brainstorm.py` — creates idea in draft state directory
- `tests/idea-cmd/test_idea_state_cli.py` — 17 test classes, heavily dependent on directory-based state
- Skills: `write-idea` skill creates ideas in `draft/` directory

## Questions and Answers

### Q1: Migration strategy

**Q:** You currently have ~36 ideas across the 5 state directories. When switching to the `active/` + `archived/` model with metadata files, what should happen to existing ideas?
- A. Big-bang migration — move all existing ideas in one commit, generating metadata files from current directory location
- B. Gradual migration — support both old and new structures simultaneously
- C. New ideas only — existing ideas stay where they are

**A:** A — Big-bang migration. Move all existing ideas to the new structure in one commit.

### Q2: Archival policy

**Q:** Which current states map to `active/` vs `archived/`? Should completed/abandoned ideas auto-archive, or is archival always an explicit user action?
- A. Archival is explicit — completed/abandoned stay in `active/` until the user archives them. Migration puts everything in `active/`.
- B. Completed/abandoned auto-archive — during migration and on future transitions to terminal states.

**A:** A — Archival is explicit. All ideas go to `active/` during migration. The user must explicitly archive.

### Q3: Metadata file contents

**Q:** Beyond lifecycle `state`, what else should the metadata file contain?
- A. Minimal — just `state`. Other metadata can be added later.
- B. State + timestamps — `state`, `created`, `updated`.
- C. Rich metadata — `state`, `created`, `updated`, `classification`, plus queryable fields.

**A:** A — Minimal. Just `state`. Other fields can be added incrementally.

### Q4: State transition behavior

**Q:** Should `i2code idea state` auto-commit after editing the metadata file?
- A. Yes, always auto-commit.
- B. No, leave uncommitted for the user.
- C. Configurable — auto-commit by default, with `--no-commit` flag.

**A:** C — Auto-commit by default, with a `--no-commit` flag to skip.

### Q5: Archive operation

**Q:** How should archiving be exposed in the CLI?
- A. Separate command — `i2code idea archive <name>` and `i2code idea unarchive <name>`. Archival is independent of lifecycle state.
- B. Part of state command — `i2code idea state <name> archive` treats "archived" as a pseudo-state.
- C. Flag on state command — `i2code idea state <name> --archive`.

**A:** A — Separate commands: `i2code idea archive` and `i2code idea unarchive`. Archival is orthogonal to lifecycle state.

### Q6: Listing and filtering

**Q:** Should `i2code idea list` show archived ideas by default?
- A. Active only by default — use `--archived` or `--all` to include archived.
- B. All by default — use `--active-only` or `--archived-only` to filter.

**A:** A — Active only by default. Use `--archived` or `--all` to include archived ideas.

### Q7: Migration script

**Q:** How should the big-bang migration be implemented?
- A. One-off script — standalone, delete after use.
- B. i2code subcommand — `i2code idea migrate`, permanent part of CLI.
- C. Manual / Claude-assisted — no script.

**A:** B — Permanent `i2code idea migrate` subcommand, useful if others adopt the tool.

### Q8: Existing wt-state.json files

**Q:** Should the new `*-metadata.yaml` and existing `*-wt-state.json` be merged or kept separate?
- A. Keep separate — different concerns (lifecycle vs. implementation runtime).
- B. Merge into metadata — consolidate into `*-metadata.yaml`.

**A:** A — Keep separate. Metadata file is for lifecycle state; wt-state.json remains for implementation runtime state.

### Q9: Transition rules

**Q:** The current transition rules (forward-only, plan-file requirements, `--force` override) are about lifecycle validation, not directory structure. Should they carry over unchanged?
- A. Keep rules as-is — same transitions, same requirements, same `--force`.
- B. Revisit rules — change some while we're at it.

**A:** A — Keep transition rules exactly as they are.

### Derived conclusions (no question needed)

- **CODEBASE.md** documents the `docs/ideas/{state}/` structure — will need updating to reflect `active/` and `archived/`.
- **`LIFECYCLE_STATES` constant** in `resolver.py` — stays the same (draft, ready, wip, completed, abandoned). These are lifecycle states, not directory names.
- **`state_from_path()`** — currently extracts state from directory path; must be replaced with metadata file reading.
- **`resolve_idea()` and `list_ideas()`** — scan `active/` and `archived/` directories, read metadata files to get state.
- **`IdeaProject`** — add `metadata_file` property (`{name}-metadata.yaml`).
- **`brainstorm.py`** — creates ideas in `active/` with metadata file set to `draft`.
- **`write-idea` skill** — references idea creation; must target `active/` and create metadata file.
- **Shell completions** — `list_ideas()` already returns idea names; just needs to scan new directories.

## Classification

**Classification: C — Platform/infrastructure capability**

**Rationale:** This is a structural change to the idea management infrastructure that underpins the entire i2code workflow. It doesn't add user-visible features (no new capabilities for end users), nor is it a POC or example. It refactors how internal state is stored and managed — a platform concern that makes the system cleaner and more maintainable. The CLI surface area changes (new `archive`/`unarchive`/`migrate` commands, `--no-commit` flag) are in service of the infrastructure change, not user-facing features.
