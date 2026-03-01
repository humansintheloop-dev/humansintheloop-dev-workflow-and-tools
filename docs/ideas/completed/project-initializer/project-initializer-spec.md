# Project Initializer - Platform Capability Specification

## Purpose and Context

The `i2code implement --isolate` workflow delegates task execution to an isolarium VM. The GitHub App token used inside the VM does not have permission to push workflow files (`.github/workflows/*`). This means the VM cannot create or modify CI pipelines.

The Project Initializer adds an `ensure_project_setup()` step that runs on the **host** (in the `--isolate` code path, before delegating to isolarium). It invokes Claude to analyze the idea/spec/plan files and generate project scaffolding - build system, placeholder code, test scripts, and a CI pipeline - then pushes and verifies the scaffolding passes CI. Only after CI is green does it delegate to the VM for task execution.

Inside the VM (the `--isolated` code path), `ensure_integration_branch()` must be updated to track the remote branch instead of creating from HEAD, so the VM picks up the scaffolding pushed by the host. Slice branches are unaffected - they are created inside the VM from the (now local) integration branch as usual.

## Consumers

- **`i2code implement --isolate`** - The host-side code path that runs `ensure_project_setup()` before delegating to isolarium.
- **`i2code implement --isolated`** - The VM-side code path that picks up the scaffolding via remote branch tracking.
- **Automated test suite** - Tests using `--mock-claude` to verify the scaffolding flow without real Claude invocations.

## Capabilities and Behaviors

### CAP-1: Project Scaffolding Generation (`ensure_project_setup()`)

Runs on the host in the `--isolate` code path, after idea file validation and before delegation to isolarium.

**Behavior:**

1. Get the repo from the idea directory.
2. Create or reuse the integration branch (`idea/{idea_name}/integration`) via `ensure_integration_branch()`.
3. Check out the integration branch.
4. Invoke Claude with a goal-oriented scaffolding prompt that references the idea/spec/plan files.
5. Claude analyzes the idea files and generates the appropriate scaffolding:
   - **Java projects:** Gradle skeleton (build.gradle, gradlew wrapper, source directories, placeholder code that compiles and passes tests).
   - **Infrastructure projects:** `test-scripts/test-end-to-end.sh` with placeholder content that exits 0.
   - **All projects:** `.github/workflows/ci.yaml` that builds and runs whatever scaffolding was created.
   - These categories are not mutually exclusive - a project may need both.
6. Claude commits the scaffolding.
7. If Claude made no commits (scaffolding already sufficient), skip push and CI wait.
8. Push the integration branch to origin.
9. Wait for CI to pass. If CI fails, use the existing `fix_ci_failure()` retry loop (respecting `--ci-fix-retries` and `--ci-timeout`).
10. Only after CI passes, delegate to isolarium.

**Claude invocation details:**

- Respects `--non-interactive` flag: uses `run_claude_interactive()` in interactive mode, `run_claude_with_output_capture()` in non-interactive mode.
- Supports `--mock-claude`: when set, invokes the mock script with a distinguishable argument (e.g., `mock_script setup`) instead of real Claude.
- Always runs on every invocation - Claude decides whether changes are needed based on the current state of the repo.
- The prompt is goal-oriented: describes the desired outcome (minimal buildable project with passing CI, placeholder code) and constraints, but does not prescribe specific versions or templates. Versions and technology choices come from the idea/spec/plan files.

### CAP-2: Integration Branch Remote Tracking (`ensure_integration_branch()`)

Modify the existing `ensure_integration_branch()` function to support remote tracking in `--isolated` mode.

**Current behavior (unchanged for non-isolated mode):**

- If the local branch `idea/{idea_name}/integration` does not exist, create it from HEAD.

**New behavior when `--isolated` (inside the VM):**

1. If the local branch exists, use it (no change).
2. If the local branch does not exist, check if `origin/idea/{idea_name}/integration` exists on the remote.
3. If the remote branch exists, create a local tracking branch from it.
4. If neither local nor remote branch exists, create from HEAD (fallback).

This ensures the VM picks up the scaffolding and any prior work pushed by the host.

**API change:** Add an `isolated` parameter (default `False`) to `ensure_integration_branch()` to control the remote-tracking behavior.

## High-Level APIs, Contracts, and Integration Points

### New Function: `ensure_project_setup()`

```python
def ensure_project_setup(
    repo: Repo,
    idea_directory: str,
    idea_name: str,
    integration_branch: str,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    ci_fix_retries: int = 3,
    ci_timeout: int = 600,
    skip_ci_wait: bool = False
) -> bool:
    """Ensure project scaffolding exists on the integration branch.

    Returns True if setup succeeded (CI passes), False otherwise.
    """
```

### New Function: `build_scaffolding_prompt()`

```python
def build_scaffolding_prompt(
    idea_directory: str,
    interactive: bool = True
) -> List[str]:
    """Build the Claude command for project scaffolding.

    Returns command as a list suitable for subprocess.
    """
```

### Modified Function: `ensure_integration_branch()`

```python
def ensure_integration_branch(
    repo: Repo,
    idea_name: str,
    isolated: bool = False     # new parameter
) -> str:
```

### CLI Integration Point

In `cli.py`, the `--isolate` code path (lines 77-102) must be restructured:

**Before (current):** Validate idea files -> delegate to isolarium immediately.

**After:** Validate idea files -> create integration branch -> `ensure_project_setup()` -> delegate to isolarium.

The `--isolated` code path (lines 126-135) must pass `isolated=True` to `ensure_integration_branch()`.

## Non-Functional Requirements and SLAs

- **CI green baseline:** The integration branch must have passing CI before any slice branch work begins. This is enforced by waiting for CI after pushing scaffolding.
- **Idempotency:** Running `ensure_project_setup()` multiple times must not break existing scaffolding. Claude sees the current state and acts accordingly.
- **Testability:** All new functions support `--mock-claude` for automated testing without real Claude invocations.
- **Backward compatibility:** Non-isolated workflows (`i2code implement` without `--isolate`) are unaffected. The `isolated` parameter on `ensure_integration_branch()` defaults to `False`.

## Scenarios and Workflows

### Scenario 1 (Primary): First-time Java project setup with `--isolate`

**Preconditions:** A new idea directory with idea/spec/plan files describing a Java service. No integration branch exists. No scaffolding exists in the repo.

**Flow:**
1. User runs `i2code implement --isolate docs/features/my-service/`.
2. Host validates idea files.
3. Host creates integration branch `idea/my-service/integration` from HEAD.
4. Host checks out the integration branch.
5. Host invokes Claude with the scaffolding prompt referencing the idea files.
6. Claude reads the idea files, determines it's a Java project, and generates:
   - `build.gradle` / `settings.gradle` with appropriate versions from the idea files.
   - `gradlew` wrapper.
   - Placeholder `src/main/java/...` and `src/test/java/...` with a passing test.
   - `.github/workflows/ci.yaml` that runs `./gradlew build`.
7. Claude commits the scaffolding.
8. Host pushes integration branch to origin.
9. Host waits for CI. CI passes.
10. Host delegates to isolarium: `isolarium run -- i2code implement --isolated ...`.
11. Inside the VM, `ensure_integration_branch(isolated=True)` finds `origin/idea/my-service/integration` and creates a local tracking branch.
12. Slice branch is created from the (now local) integration branch. Task execution proceeds, inheriting the scaffolding.

### Scenario 2: Infrastructure project with `test-end-to-end.sh`

**Preconditions:** Idea files describe an infrastructure setup (e.g., Docker Compose environment).

**Flow:**
1-4. Same as Scenario 1.
5. Claude reads the idea files, determines it's an infrastructure project, and generates:
   - `test-scripts/test-end-to-end.sh` (executable, exits 0 as placeholder).
   - `.github/workflows/ci.yaml` that runs `./test-scripts/test-end-to-end.sh`.
6-12. Same as Scenario 1.

### Scenario 3: Hybrid project (Java + infrastructure)

**Preconditions:** Idea files describe a Java service with Docker Compose infrastructure.

**Flow:**
1-4. Same as Scenario 1.
5. Claude generates both Gradle skeleton and `test-scripts/test-end-to-end.sh`, with `ci.yaml` running both `./gradlew build` and the test script.
6-12. Same as Scenario 1.

### Scenario 4: Repeated run (scaffolding already exists)

**Preconditions:** Integration branch already exists with scaffolding from a previous run. Remote has the branch.

**Flow:**
1-3. Host finds existing integration branch and checks it out.
4. Host invokes Claude. Claude sees existing scaffolding and makes no commits.
5. Host detects no new commits - skips push and CI wait.
6. Host delegates to isolarium.

### Scenario 5: Scaffolding CI failure with retry

**Preconditions:** Claude generates scaffolding that fails CI (e.g., Gradle build error).

**Flow:**
1-8. Same as Scenario 1.
9. Host waits for CI. CI fails.
10. Host enters `fix_ci_failure()` loop: fetches logs, invokes Claude to fix, pushes, waits for CI again.
11. CI passes on retry.
12. Host delegates to isolarium.

### Scenario 6: Integration branch exists on remote but not locally (VM fresh clone)

**Preconditions:** Inside the VM (`--isolated`). The repo is a fresh clone. `origin/idea/my-service/integration` exists from a previous host run.

**Flow:**
1. `ensure_integration_branch(repo, "my-service", isolated=True)` is called.
2. Local branch `idea/my-service/integration` does not exist.
3. Remote ref `origin/idea/my-service/integration` exists.
4. Local tracking branch is created from the remote ref.
5. The branch includes all scaffolding from the host.

## Constraints and Assumptions

- **Host has full git push permissions** including workflow files. The GitHub App token limitation only applies inside the isolarium VM.
- **Claude is available on the host** and can be invoked for scaffolding generation.
- **The repo has a GitHub remote** (`origin`) for pushing branches and CI integration.
- **`gh` CLI is available** on the host for CI monitoring (`gh run list`, `gh run watch`).
- **Idea files contain enough information** for Claude to infer the project type and technology versions.
- **The `--isolate` code path currently delegates immediately** to isolarium (lines 77-102 of `cli.py`). This is the insertion point for `ensure_project_setup()`.

## Acceptance Criteria

1. **AC-1:** Running `i2code implement --isolate` on a new Java idea directory creates a Gradle skeleton, `ci.yaml`, and placeholder code on the integration branch, pushes it, and CI passes before delegation to isolarium.
2. **AC-2:** Running `i2code implement --isolate` on a new infrastructure idea directory creates `test-scripts/test-end-to-end.sh`, `ci.yaml`, and CI passes.
3. **AC-3:** Running `i2code implement --isolate` when scaffolding already exists does not break existing scaffolding and proceeds to delegation.
4. **AC-4:** Inside the VM (`--isolated`), `ensure_integration_branch()` creates a local tracking branch from the remote when the local branch doesn't exist.
5. **AC-5:** If scaffolding CI fails, the existing `fix_ci_failure()` retry loop is invoked and can fix the issue.
6. **AC-6:** `--mock-claude` can be used to test the full scaffolding flow without real Claude invocations.
7. **AC-7:** Non-isolated workflows (`i2code implement` without `--isolate`) are unaffected by these changes.
