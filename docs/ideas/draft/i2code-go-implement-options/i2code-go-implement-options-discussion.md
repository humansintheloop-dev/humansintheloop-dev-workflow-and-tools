# i2code-go-implement-options Discussion

## Classification

**A. User-facing feature**

Rationale: This enhances the `i2code go` interactive menu — a direct user-facing workflow. It improves discoverability of implementation options and streamlines the configure-then-commit flow. No architectural changes, no new infrastructure, no POC validation needed.

## Context from Codebase Analysis

- `implement_config.py` already exists with 2 configurable options: interactive (bool) and trunk (bool)
- Config stored in `{name}-implement-config.yaml` in the idea directory
- "Configure implement options" menu item currently only appears after config file already exists
- `isolation_type` already exists as a CLI argument (`--isolation-type TYPE`) and in `ImplementOpts`, but is not part of the menu-driven config
- Three execution modes: worktree (default), trunk, isolate (VM-based via isolarium)
- `--isolation-type` or `--shell` automatically enables `--isolate` in `ImplementCommand`

## Questions and Answers

### Q1: Menu flow for configuration

**A: Always show "Configure implementation options" in the menu.** Label changes to "Revise implementation options" once config exists. If no config exists when user selects "Implement", it prompts for config first (existing `_ensure_implement_config()` behavior).

### Q2: Default menu selection in HAS_PLAN state

**A: "Configure implementation options" is the default when no config exists.** Once config is set, "Commit changes" becomes the default (if uncommitted changes exist).

### Q3: Isolation type and question flow

**Answer: Ask isolation type first, only ask trunk/worktree if isolation is "none".** This makes sense because trunk + isolate is invalid, and any isolation type implies worktree mode. The config prompt flow becomes:

1. "How should Claude run?" → Interactive / Non-interactive
2. "Isolation type?" → None / Nono / Container / VM
3. (Only if isolation = none) "Where should implementation happen?" → Worktree / Trunk

### Q4: Config completeness when isolation is set

**A: Explicitly set trunk=false in config.** The YAML file always has all three fields (interactive, isolation_type, trunk), making the config self-documenting.

### Q5: Config file format change / backward compatibility

**A: Auto-migrate on read.** If `isolation_type` is missing from an existing config file, treat it as `none` and continue without re-prompting.

### Q6: Menu ordering in HAS_PLAN state

**A: Confirmed.** The menu order is:

Before config exists:
1. Revise the plan
2. Configure implementation options [default]
3. Commit changes
4. Implement the entire plan: i2code implement
5. Exit

After config exists:
1. Revise the plan
2. Revise implementation options
3. Commit changes [default]
4. Implement the entire plan: i2code implement {flags from config}
5. Exit

### Q7: Position of "Move to ready/wip" menu item

**A: Between "Revise implementation options" and "Commit changes"** (position 3, pushing others down). Full menu when all items are visible:

1. Revise the plan
2. Configure/Revise implementation options
3. Move to ready/wip (conditional)
4. Commit changes
5. Implement the entire plan: i2code implement {flags}
6. Exit
