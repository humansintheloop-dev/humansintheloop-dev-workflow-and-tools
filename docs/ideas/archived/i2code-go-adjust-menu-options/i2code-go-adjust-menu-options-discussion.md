# Discussion: i2code-go-adjust-menu-options

## Classification

**Type: A. User-facing feature**

**Rationale**: This changes the interactive menu UX of `i2code go` to better guide users through the workflow by reordering options and setting context-aware defaults. It affects only the user-facing menu presentation, not architecture or infrastructure.

## Codebase Analysis

The relevant code is in `src/i2code/go_cmd/orchestrator.py`:

- `_build_has_plan_options()` (line 311): builds the list of menu options for HAS_PLAN state
- `_commit_default()` (line 329): determines which option is the default
- `_lifecycle_move_label()` (line 298): reads metadata to determine available state transition
- `_dispatch_has_plan()` (line 263): presents the menu and dispatches the selected action

The lifecycle state is already available via `read_metadata()` from `i2code.idea.metadata`. The implement config existence is checked via `os.path.isfile(self._project.implement_config_file)`.

## Q&A

### Q1: How should the system determine which default to show?

**Answer**: Based on the idea's lifecycle state from metadata (after confirming the plan file exists). The plan file existence triggers the HAS_PLAN state; after that, the metadata state drives the default.

### Q2: Should the Configure/Revise implement options always be visible?

**Answer**: Yes, always visible. The label switches between "Configure" and "Revise" based on whether the config file exists (current behavior preserved).

### Q3: Default mapping confirmation

**Confirmed mapping**:

| State | Default |
|---|---|
| draft (plan exists) | Move idea to ready |
| ready | Configure/Revise implement options |
| wip, uncommitted changes | Commit changes |
| wip, no uncommitted changes | Implement the entire plan |

### Q4: Should the option order be stable or optimized per state?

**Answer**: Stable order. The relative position of options never changes; options appear/disappear but maintain consistent ordering across all states.

### Q5: What should happen when metadata state is unknown or missing?

**Answer**: Fall back to option 2 (Configure implement options) as the default.
