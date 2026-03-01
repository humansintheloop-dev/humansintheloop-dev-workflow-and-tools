# Project Initializer - Discussion

## Context

The `i2code implement` workflow currently validates idea files and creates Git branch infrastructure (integration branch, slice branches, worktrees) before invoking Claude to execute tasks from a plan file. However, there is no step to ensure the project has the basic scaffolding (build system, CI pipeline, test scripts) before task execution begins.

The proposed `ensure_project_setup()` would run after branch creation but before task execution, invoking Claude to analyze the idea files and generate appropriate project scaffolding.

## Questions and Answers

### Q1: How should the project type be determined?

**Options:**
- A. Claude infers it entirely from the idea/spec files (most flexible, but less predictable)
- B. An explicit `project-type` field in the idea file
- C. Convention-based on directory structure or naming patterns
- D. A combination: Claude infers, user confirms or overrides

**Answer:** A - Claude infers from the idea/spec/plan files.

**Implication:** The prompt to Claude must include clear instructions for what scaffolding to generate based on what it reads. The output is non-deterministic, so we need to verify the result (e.g., build files exist, CI pipeline is valid) rather than relying on exact expected output.

### Q2: When should `ensure_project_setup()` run?

**Options:**
- A. Only in `--isolate`/`--isolated` mode (as the idea file states)
- B. In both isolated and normal worktree mode
- C. In both modes, but with different behavior

**Answer:** A - Only in `--isolate`/`--isolated` mode.

**Implication:** The feature is scoped to the isolated execution path. In the normal worktree workflow, the user is expected to have set up the project themselves (or it's already set up). This simplifies the implementation since we only need to handle the `--isolated` code path.

### Q3: Which branch should the scaffolding be committed to?

**Options:**
- A. The integration branch directly (before slice branch checkout) - so all slices inherit the scaffolding
- B. The slice branch - scaffolding is just part of the first slice's work

**Answer:** A - The integration branch directly.

**Implication:** `ensure_project_setup()` must run while on the integration branch, before the slice branch is checked out. The scaffolding commit(s) land on the integration branch, and when slice branches are created from it, they automatically include the scaffolding. This also means the integration branch gets pushed with the scaffolding, so it's available to all future slices. The flow becomes: create integration branch → ensure project setup → push integration branch → create/checkout slice branch → execute tasks.

### Q4: Should `ensure_project_setup()` be idempotent?

**Options:**
- A. Skip entirely if scaffolding already exists
- B. Always re-run Claude and let Claude decide whether changes are needed
- C. Check for specific markers (e.g., `.project-initialized` file) to decide

**Answer:** B - Always re-run Claude and let Claude decide.

**Implication:** The function always invokes Claude with the idea files and the current state of the repo. If scaffolding already exists, Claude sees it and either makes no changes or updates it. This is simpler to implement (no detection logic needed) and more flexible (Claude can evolve scaffolding as the idea evolves). The trade-off is a Claude invocation on every run, even when nothing changes.

### Q5: How should `ensure_integration_branch()` handle remote branches in `--isolated` mode?

**Options:**
- A. If the remote already has the integration branch, check it out and track it rather than creating a new one from HEAD
- B. Always create from HEAD, and force-push if the remote branch already exists
- C. Create from HEAD if no remote branch exists; otherwise fetch and reset to the remote branch

**Answer:** A - If the integration branch does not exist in the local repo, create it from the remote.

**Implication:** In `--isolated` mode (inside an isolarium VM with a fresh clone), `ensure_integration_branch()` needs modified behavior: check if `origin/idea/{name}/integration` exists, and if so, create a local tracking branch from it. This preserves scaffolding and prior work from previous runs. Only if the remote branch doesn't exist either should it create a new branch from HEAD. This is a change to the existing `ensure_integration_branch()` function (or a new variant for the isolated path).

### Q6: Should `ci.yaml` always be generated?

**Options:**
- A. Always generate `ci.yaml` - every project should have CI from the start
- B. Only generate `ci.yaml` when there's something to build

**Answer:** A - Always generate `ci.yaml`. It should test the placeholder code that is also created (e.g., `gradlew`, `test-end-to-end.sh`).

**Implication:** The scaffolding must be internally consistent: if a Gradle skeleton is created, `ci.yaml` runs `./gradlew build`; if `test-scripts/test-end-to-end.sh` is created, `ci.yaml` calls it. The placeholder code must be valid and passing so that CI is green from the very first push. Note: the correct test script name is `test-end-to-end.sh` (not `test-end-to-end-tests.sh` as originally written in the idea file).

### Q7: Should CI be verified after scaffolding is pushed?

**Options:**
- A. Yes - wait for CI to pass on the integration branch before proceeding
- B. No - just push and move on

**Answer:** A - Wait for CI to pass on the integration branch before proceeding.

**Implication:** After pushing the integration branch with scaffolding, the existing `wait_for_workflow_completion()` and CI failure handling logic can be reused. If CI fails, `ensure_project_setup()` should fix it (similar to the existing CI fix retry loop) before proceeding. This guarantees a green baseline for all slice branches. The existing `ci_fix_retries` and `ci_timeout` parameters apply here too.

### Q8: How should Claude be invoked for the scaffolding step?

**Options:**
- A. Non-interactively (`-p` flag) with a specialized scaffolding prompt - fully automated
- B. Interactively - the user can guide the scaffolding process
- C. Follow the same mode as the main task execution (respect the `--non-interactive` flag)

**Answer:** C - Follow the same mode as the main task execution.

**Implication:** The scaffolding invocation reuses the interactive/non-interactive mode determined by `--non-interactive`. A new `build_scaffolding_prompt()` function constructs a prompt focused on project setup (not task execution), but the invocation mechanism (`run_claude_with_output_capture()` vs `run_claude_interactive()`) follows the same pattern as task execution.

### Q9: Are Java/Gradle and infrastructure scaffolding mutually exclusive?

**Options:**
- A. Mutually exclusive - either Java service OR infrastructure project
- B. They can overlap - a project might need both Gradle skeleton AND infrastructure test scripts
- C. There are more categories to consider

**Answer:** B - They can overlap.

**Implication:** The scaffolding prompt to Claude should not force a single project type. Instead, it should instruct Claude to analyze the idea and determine which scaffolding components are needed. A Java service with Docker Compose infrastructure would get both a Gradle skeleton and `test-scripts/test-end-to-end.sh`, with `ci.yaml` running both `./gradlew build` and the test script. Claude's flexibility (from Q1) naturally handles this - it reads the idea and generates all applicable scaffolding.

### Q10: How prescriptive should the scaffolding prompt be?

**Options:**
- A. Highly prescriptive - enumerate exact files and templates with specific versions
- B. Goal-oriented - describe desired outcome and constraints, let Claude choose specifics
- C. Template-based - provide actual file templates that Claude fills in

**Answer:** B - Goal-oriented. The idea files often specify versions, so Claude can pick them up from there.

**Implication:** The prompt describes the goal (e.g., "create a minimal buildable project with passing CI") and constraints (e.g., "use placeholder code that compiles and passes tests"), but defers specifics like Java version, Spring Boot version, etc. to what the idea/spec files say. This keeps the prompt stable across different projects while letting the idea files drive the details.

### Q11: Should slice branch also track remote in `--isolated` mode?

**Derived conclusion:** No. Slice branches are created inside the VM from the integration branch (which is already local after `ensure_integration_branch()` tracks the remote). The existing `ensure_slice_branch()` logic works as-is - only the integration branch needs remote tracking because it is created on the host and consumed in the VM.

**Code note:** `implement.py:211` (`repo.create_head(branch_name)`) in `ensure_integration_branch()` needs to change for `--isolated` mode - should create from `origin/{branch_name}` when the remote branch exists, rather than from HEAD.

### Q12: Should `ensure_project_setup()` use the `--mock-claude` mechanism for testing?

**Options:**
- A. Yes - follow the same `--mock-claude` pattern for testability
- B. No - test differently

**Answer:** A - Follow the same `--mock-claude` pattern.

**Implication:** `ensure_project_setup()` accepts a `mock_claude` parameter. When set, the mock script is invoked instead of real Claude, with a distinguishable argument (e.g., `mock_script setup`) so the mock can produce appropriate scaffolding output. This enables automated testing of the full flow without real Claude invocations.

### Motivation (added after Q12)

The GitHub App token used inside the isolarium VM does not have permission to push workflow files (`.github/workflows/*`). Therefore, `ensure_project_setup()` must run on the **host** in the `--isolate` code path (before delegating to isolarium), not inside the `--isolated` path (inside the VM). The host has full git permissions.

**Revised flow:**
1. **Host (`--isolate`):** create integration branch → `ensure_project_setup()` (scaffolding + `ci.yaml`) → commit → push → wait for CI to pass → delegate to isolarium
2. **VM (`--isolated`):** `ensure_integration_branch()` tracks the remote integration branch (picks up scaffolding) → create/track slice branch → execute tasks

This is why `ensure_integration_branch()` must track the remote in `--isolated` mode - the scaffolding was pushed by the host and the VM needs to pick it up.

## Classification

**Category:** C - Platform/infrastructure capability

**Rationale:** This feature enhances the internal `i2code implement` workflow by adding automated project scaffolding. It is not user-facing (end users don't interact with it directly), not an architecture POC (the approach is well-understood), and not an educational example. It is a platform capability that makes the implement pipeline more robust by ensuring projects have a buildable, CI-tested foundation before task execution begins. It extends existing infrastructure (branch management, Claude invocation, CI monitoring) with a new lifecycle step.

