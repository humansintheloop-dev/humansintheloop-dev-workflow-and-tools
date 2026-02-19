# Discussion: i2code idea-to-code subcommand

## Classification

**Type: A. User-facing feature**
**Rationale:** This packages existing user-facing workflow scripts into a unified, installable CLI — improving distribution and usability without changing core functionality.

## Questions and Answers

### Q1: What is the scope of scripts to convert?

**Options presented:**
- A. Core workflow only — just the scripts idea-to-code.sh calls directly
- B. Core workflow + analysis scripts
- C. Everything — all scripts in workflow-scripts/ (excluding implement-plan.sh and implement-with-worktree.sh)
- D. Just the orchestrator

**Answer: C — Everything.**

All scripts in `workflow-scripts/` will be converted, excluding:
- `implement-plan.sh` (already replaced by `i2code implement`)
- `implement-with-worktree.sh` (backward-compat wrapper for the above)

### Q2: How should the shell scripts be packaged as i2code subcommands?

**Derived conclusion:** Since the user wants `i2code <subcommand>` invocation and the idea says "initially they would be shell scripts," the approach is:

**Answer: Click wrappers that exec the bundled shell scripts.**

- Python Click commands registered under the existing `i2code` CLI group
- Each command locates and `subprocess.run()`s the bundled `.sh` file
- Shell scripts shipped as package data, logic stays untouched initially
- This allows incremental rewrite to Python later

### Q3: Should the orchestrator become a subcommand too, or only individual steps?

**Options presented:**
- A. Both — orchestrator + individual step commands
- B. Orchestrator only — individual steps are internal
- C. Individual steps only — no orchestrator

**Answer: A — Both.**

The orchestrator and individual steps will both be subcommands.

### Q4: How should the new subcommands be organized in the CLI namespace?

**Discussion:** `i2code idea-to-code` is redundant since `i2code` already stands for "idea to code." Several grouping options were explored.

**Answer: `idea-to-plan` group** (user suggestion).

This describes the phase and creates a clear workflow progression:
- `i2code idea-to-plan` — develop the idea into a plan
- `i2code plan` — manage an existing plan file (already exists)
- `i2code implement` — execute the plan (already exists)

Core workflow subcommands:
- `i2code idea-to-plan run` — orchestrator (replaces idea-to-code.sh)
- `i2code idea-to-plan brainstorm`
- `i2code idea-to-plan spec`
- `i2code idea-to-plan revise-spec`
- `i2code idea-to-plan make-plan`
- `i2code idea-to-plan revise-plan`
- `i2code idea-to-plan design-doc`

### Q5: How should the remaining (non-workflow) scripts be grouped?

**Answer:** Analysis and review scripts become subcommands of `improve`:
- `i2code improve analyze-sessions`
- `i2code improve summary-reports`
- `i2code improve review-issues`
- `i2code improve update-claude-files` (from update-claude-files-from-project.sh)

### Q6: Where do the remaining scripts go?

**Remaining scripts:**
- `setup-claude-files.sh` — initial setup of Claude files
- `update-project-claude-files.sh` — updates project's Claude files
- `implement-todo-list.sh` — lightweight Claude wrapper to implement a todo-list file
- `refine-todo-list.sh` — lightweight Claude wrapper to break todo items into atomic tasks

**Answer:**
- Setup scripts → `i2code setup` subcommands:
  - `i2code setup claude-files` (from setup-claude-files.sh)
  - `i2code setup update-project` (from update-project-claude-files.sh)
- Todo scripts → **Deferred.** Excluded from initial scope — they're simple standalone scripts, can be converted later.

### Q7: How should `_helper.sh` be handled?

**Answer:** Bundle as package data alongside the shell scripts. Scripts source it relative to their own location, keeping them self-contained.

### Q8: How should `_python_helper.sh` be handled?

**Answer:** Drop it. No script in `workflow-scripts/` sources it — it's dead code.

### Q9: How should `prompt-templates/` be handled?

11 scripts reference prompt templates via `$DIR/../prompt-templates/`.

**Answer: A — Bundle as package data.** Prompt templates are shipped with the package.

### Q12: What should happen to the original scripts in `workflow-scripts/`?

**Options presented:**
- A. Remove them
- B. Keep as symlinks
- C. Keep as thin wrappers
- D. Leave in place (duplicated)

**Answer: A — Remove them.** The `i2code` subcommands are the only invocation path going forward. Original scripts in `workflow-scripts/` are deleted after migration.

### Q14: How should the skill name list be provided?

Two scripts (`make-plan.sh`, `create-design-doc.sh`) list skill names from `$DIR/../skills` for prompt substitution. Only the names are needed, not the content.

**Options considered:**
- A. Hardcode in the scripts
- B. Discover from `~/.claude/plugins/cache/`
- C. Pass as a script argument

**Answer: B — Discover from `~/.claude/plugins/cache/` via a helper script.** A helper script will locate the installed plugin's skills directory under `~/.claude/plugins/cache/` and list the skill names. This is more dynamic than hardcoding, though it depends on the Claude CLI plugin cache path structure.

### Q13: How should `config-files/` be handled?

Three scripts reference `$DIR/../config-files`: `setup-claude-files.sh`, `update-project-claude-files.sh`, and `update-claude-files-from-project.sh`.

**Answer:** The config directory should be specified as a script argument. The scripts will be modified to accept the config directory path as a parameter rather than deriving it from `$DIR/..`.

### Q15: What about `workflow-scripts/requirements.txt`?

**Answer:** Drop it. It was for `_python_helper.sh` (dead code). Dependencies are already in `pyproject.toml`.

### Q11: What should the Python Click wrapper be responsible for?

**Options presented:**
- A. Minimal passthrough — just CLI registration and script discovery
- B. Argument parsing + passthrough
- C. Full argument ownership
- D. Progressive — start minimal, refactor later

**Answer: A — Minimal passthrough.** The Click wrapper only handles CLI registration and locating the bundled shell script. All arguments, validation, and session management stay in the shell scripts.

### Q10: Package data directory layout?

**Answer:** Place shell scripts in `src/i2code/scripts/` and prompt templates in `src/i2code/prompt-templates/`. These are siblings under `src/i2code/`, so the existing `$DIR/../prompt-templates/` references in the shell scripts resolve correctly without modification.
