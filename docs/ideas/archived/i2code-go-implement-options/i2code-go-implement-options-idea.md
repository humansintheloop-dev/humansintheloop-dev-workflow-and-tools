# i2code go: Implementation Options Configuration

## Problem

When a plan has been created, `i2code go` displays a menu that jumps straight to "Commit changes" and "Implement" without prompting the user to configure how implementation should run. The "Configure implement options" menu item only appears after a config file already exists, making it easy to miss.

Implementation options were previously implemented but disappeared at some point. The goal is to bring them back with improved UX — configuring options before committing.

## Desired Behavior

### Menu: Before config exists

```
Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Configure implementation options [default]
  3) Move to ready/wip (conditional)
  4) Commit changes
  5) Implement the entire plan: i2code implement
  6) Exit
```

### Menu: After config exists

```
Implementation plan exists. What would you like to do?
  1) Revise the plan
  2) Revise implementation options
  3) Move to ready/wip (conditional)
  4) Commit changes [default]
  5) Implement the entire plan: i2code implement --non-interactive --isolation-type nono
  6) Exit
```

## Configuration Prompt Flow

The config prompt asks three questions in order, with conditional logic:

1. **How should Claude run?** → Interactive (default) / Non-interactive
2. **Isolation type?** → None (default) / Nono / Container / VM
3. **Where should implementation happen?** (only if isolation = none) → Worktree (default) / Trunk

When isolation type is not "none", trunk is automatically set to false (worktree mode is implied).

## Config Storage

Options saved in `{name}-implement-config.yaml` in the idea directory with three fields:

```yaml
interactive: true
isolation_type: none
trunk: false
```

Backward compatibility: existing config files missing `isolation_type` are treated as `isolation_type: none` (auto-migrate on read, no re-prompt).

## Key Design Decisions

- "Configure/Revise implementation options" always appears in the HAS_PLAN menu (not just after config exists)
- Default menu selection: "Configure implementation options" when no config exists, "Commit changes" when config exists
- All three fields always written to config (self-documenting)
- The "Implement" menu label shows the exact flags that will be used
