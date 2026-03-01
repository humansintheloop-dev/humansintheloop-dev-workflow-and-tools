# Discussion: Migrate i2code go Scripts from Bash to Python

## Classification

**Type: C. Platform/infrastructure capability**

**Rationale:** This migrates internal CLI tooling from bash to Python without changing user-facing behavior. The `i2code go` CLI interface and workflow remain the same; the implementation language changes. This improves the platform's maintainability and testability.

## Codebase Analysis (Pre-Discussion)

### Current Architecture
- `idea-to-code.sh` (18KB) is a bash state machine orchestrating: idea -> spec -> plan -> implement
- It calls: `brainstorm-idea.sh`, `make-spec.sh`, `revise-spec.sh`, `make-plan.sh`, `revise-plan.sh`, `list-plugin-skills.sh`
- All scripts source `_helper.sh` for shared environment variables and validation functions
- Python CLI already wraps these scripts via `script_command()` / `script_runner.py`
- The `implement` command is already pure Python (complex orchestration with worktree, PR, CI)
- Bash tests exist in `test-scripts/` (e.g., `test-i2code-go.sh`, `test-implement-config.sh`)

### Scripts to Migrate (in workflow order)
1. `idea-to-code.sh` — Main orchestrator (state machine, menus, config management)
2. `brainstorm-idea.sh` — Ideation workflow (editor launch, session management, Claude invocation)
3. `make-spec.sh` — Specification creation (template loading, Claude invocation)
4. `revise-spec.sh` — Specification revision
5. `make-plan.sh` — Plan creation (template loading, AWK validation, Claude auto-repair)
6. `revise-plan.sh` — Plan revision
7. `list-plugin-skills.sh` — Plugin skill enumeration
8. `_helper.sh` — Shared environment and validation (becomes Python module)

### Existing Python Infrastructure
- Click-based CLI (`cli.py`)
- `IdeaProject` value object for directory + derived paths
- `script_command()` factory pattern
- `script_runner.py` for subprocess execution
- Prompt template system in `prompt-templates/`

## Questions and Answers

### Q1: Motivation

**Q:** What's the primary motivation for this migration?
A. Testability — pytest over fragile bash tests
B. Maintainability — better structure for 18KB state machine
C. Feature velocity — easier to build upcoming features
D. Consistency — match the already-Python `implement` command

**A:** All of the above. Testability, maintainability, feature velocity, and consistency are all drivers.

### Q2: Architectural Approach

**Q:** When migrating `idea-to-code.sh` to Python, should we:
A. Mirror the bash structure — translate directly, lowest risk
B. Adopt the `implement` command's patterns — factory/strategy, more consistent
C. Rethink the architecture — redesign from scratch, highest risk

**A:** Use the command/assembler/strategy patterns already established in the Python codebase. The goal is maintainable, testable, and tested Python code. Not a direct translation of bash, but not a full redesign either — adopt proven patterns from `implement`.

### Q3: Handling Mixed-Language Transition

**Q:** How should the Python orchestrator handle calling not-yet-migrated bash scripts during the incremental migration?
A. Adapter pattern — Python interfaces with bash-delegating adapters, replaced one by one
B. Direct subprocess calls — Use existing `script_runner.py`, replace each call site when ready
C. Migrate bottom-up instead — Start with leaves, orchestrator last

**A:** Direct subprocess calls via `script_runner.py`. Keep it simple — the infrastructure for calling bash scripts already exists. Replace each call site when the Python version of that script is ready.

### Q4: Interactive Menu System

**Q:** What should the Python menu/interactive prompt system use?
A. Simple `input()` with numbered options — matches bash `select`, no dependencies, easy to test
B. `click.prompt` with choices — stay in Click ecosystem
C. `questionary` or `InquirerPy` — rich interactive menus, new dependency
D. `rich.Prompt` — if already a dependency

**A:** Simple `input()` with numbered options. Matches current bash `select` behavior, no new dependencies, and easiest to test by mocking `input()`.

### Derived Defaults (stated between Q4 and Q5)

- **Template handling:** Use `string.Template` (same `$VARIABLE` syntax as `envsubst`), zero template changes needed.
- **`_helper.sh` replacement:** Extend existing `IdeaProject` value object with missing paths and validation methods.
- **Plan validation:** Rewrite `make-plan.sh`'s AWK validator as a Python function.
- **Claude invocation:** Reuse `claude_runner.py` strategy pattern from `implement`.
- **Testing:** TDD with pytest. Bash tests become obsolete per-script as each is migrated.

### Q5: Migration Scope

**Q:** What's the scope of "the remaining scripts"?
A. Only `i2code go` workflow scripts (7 scripts). Utility scripts stay as bash.
B. All bash scripts in the project — full elimination of bash.

**A:** All bash scripts in the project. Full elimination of bash from the codebase.

**Derived consequence:** Once all scripts are migrated, `script_command.py`, `script_runner.py`, and the `scripts/` directory are deleted. Click commands call Python functions directly.

### Q6: CLI Interface After Migration

**Q:** After migration, should we keep both the orchestrator (`i2code go`) and direct subcommands (`i2code spec create`, etc.)?
A. Keep both paths — orchestrator as guided experience, subcommands for direct access
B. Orchestrator only — retire direct subcommands
C. Subcommands only — retire orchestrator

**A:** Keep both paths. `i2code go` remains the primary guided experience with menus. Direct subcommands also work independently. Same as today.
