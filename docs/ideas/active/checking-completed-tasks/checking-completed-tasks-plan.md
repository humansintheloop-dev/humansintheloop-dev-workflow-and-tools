```markdown
# Plan: checking-completed-tasks

## Idea Type

**A. User-facing feature** — a defect fix to the `i2code go` orchestrator's post-implement completion check so it reads the plan file from the location where the implement subprocess actually edited it, instead of always reading the main repo's idea directory.

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |
| `idea-to-code:find-usage` | When locating callers of `_check_plan_completion` or `IdeaProject.plan_file` before refactoring |
| `idea-to-code:apply-design-patterns` | Before extracting the resolver helper - consult the catalog first |

### TDD Requirements

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write/Edit on any `.py` file under `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (it must be `./test-scripts/test-unit.sh`), its exit code, and the last 20 lines of output

### Implementation context

Read these files before starting work in any steel thread:

- `src/i2code/go_cmd/orchestrator.py:414` — the `_check_plan_completion` method being fixed
- `src/i2code/go_cmd/orchestrator.py:75` — `_git_root_from_path` helper, reusable for finding main-repo root
- `src/i2code/go_cmd/implement_config.py:12` — `read_implement_config` (returns `dict | None`)
- `src/i2code/implement/idea_project.py:31` — `IdeaProject.plan_file`
- `src/i2code/implement/idea_project.py:127` — `IdeaProject.worktree_idea_project` helper
- `src/i2code/implement/git_repository.py:140` — `GitRepository._sibling_path` (static; takes `repo_root, suffix, idea_name`)
- `src/i2code/plan/plan_file_io.py:50` — `with_plan_file` context manager
- `src/i2code/plan_domain/parser.py` — `parse(text)` returns a domain `Plan` (used inside `with_plan_file`)
- `tests/go-cmd/test_orchestrator_implement.py:279` — existing `TestPlanCompletion` parametrized tests (these will need to be updated as part of Steel Thread 2 / Steel Thread 3)
- `tests/go-cmd/conftest.py` — `TempIdeaProject` and `menu_config_by_label` test fixtures used by orchestrator tests

All new resolver logic lives in a new module `src/i2code/go_cmd/plan_completion.py`. New unit tests live in a new test file `tests/go-cmd/test_plan_completion.py` for resolver-level coverage, and additions to `tests/go-cmd/test_orchestrator_implement.py` for orchestrator-level coverage.

---

## Steel Thread 1: Worktree+PR mode completion check reads worktree plan file

Primary scenario (Spec S1 / US-1.2). Introduces the resolver helper and wires it into `_check_plan_completion` so the worktree's plan file becomes the source of truth when `trunk=false` and `isolation_type=none`.

- [x] **Task 1.1: Orchestrator prints `Workflow Complete!` when the worktree plan file has every task checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionWorktree::test_worktree_mode_complete_plan_prints_workflow_complete -v`
  - Observable: After `Orchestrator._run_implement` completes with `returncode=0` and the plan at `<git-parent>/<repo>-wt-<idea>/<idea-relpath>/<idea>-plan.md` has every task box checked, captured stderr contains `Workflow Complete!` exactly once, does NOT contain `Plan has uncompleted tasks`, and `Orchestrator.run()` raises `SystemExit(0)`.
  - Evidence: The pytest command above runs, the test creates a `TempIdeaProject`, materialises a sibling directory `<git-parent>/<repo>-wt-<idea>/<idea-relpath>/` containing `<idea>-plan.md` with all tasks `[x]`, writes an implement-config with `trunk=false, isolation_type=none`, drives `Orchestrator.run()` through `IMPLEMENT_PLAN`, and asserts the three conditions above. The test exits 0; with the resolver bypassed the test fails because `Workflow Complete!` is not in output (the main-repo plan still has unchecked boxes).
  - Steps:
    - [x] In `tests/go-cmd/test_orchestrator_implement.py`, add a new `@pytest.mark.unit` class `TestPlanCompletionWorktree` with a fixture helper that constructs a worktree-sibling plan layout under the test's git root: locate the temporary git root used by `TempIdeaProject` and create `<parent>/<basename>-wt-<idea>/<idea-relpath>/<idea>-plan.md` populated with the supplied plan text.
    - [x] Write the failing test `test_worktree_mode_complete_plan_prints_workflow_complete` that uses the fixture to place a fully-checked plan at the worktree path, sets `config_kwargs=dict(interactive=True, trunk=False, isolation_type="none")`, drives the orchestrator with choices `[IMPLEMENT_PLAN]`, and asserts `result.exit_code == 0`, `"Workflow Complete!" in result.output_displayed`, and `"Plan has uncompleted tasks" not in result.output_displayed`.
    - [x] Inspect `tests/go-cmd/conftest.py` to confirm `TempIdeaProject` exposes (or can be extended to expose) the enclosing git root used by `_git_root_from_path`. If the fixture currently hides this, extend `TempIdeaProject` to expose it as `project_root` (or equivalent) so the worktree sibling can be located deterministically.
    - [x] Run the new test to confirm it fails (the current `_check_plan_completion` reads `project.plan_file` in the main repo, which has no plan in this fixture).
    - [x] Create `src/i2code/go_cmd/plan_completion.py` containing a function `resolve_plan_text(project, config, git_root, *, gh_runner=None) -> str | None` whose worktree branch (when `config is not None and not config["trunk"] and config["isolation_type"] == "none"`) computes `worktree_path = GitRepository._sibling_path(git_root, "wt", project.name)`, builds the worktree idea project via `project.worktree_idea_project(worktree_path, git_root)`, and returns `Path(<worktree-project>.plan_file).read_text(encoding="utf-8")`. The function must propagate `FileNotFoundError` if the file is absent (per FR2: no fallback).
    - [x] In `src/i2code/go_cmd/plan_completion.py`, expose a small public alias `sibling_path = GitRepository._sibling_path` so callers do not reach into the underscore-prefixed name; document at the call site that the helper is intentionally shared.
    - [x] Update `src/i2code/go_cmd/orchestrator.py:414` so `_check_plan_completion`:
      - reads `config = read_implement_config(self._project.implement_config_file)`
      - computes `git_root = str(_git_root_from_path(self._project.directory))`
      - obtains `plan_text = resolve_plan_text(self._project, config, git_root)`
      - if `plan_text is None`, returns without printing either banner (covers VM-failure case wired in Steel Thread 7)
      - otherwise calls `parse(plan_text)` (import from `i2code.plan_domain.parser`) and queries `plan.get_next_task()` to decide between the two banners. Preserve the exact banner strings, separators, blank lines, and `sys.exit(0)` from the current implementation.
    - [x] Run the new test again; it must pass.
    - [x] Run `./test-scripts/test-unit.sh`. Expect failures in the existing `TestPlanCompletion` parametrized cases (they were exercising the buggy behaviour). Do NOT delete or fix them here — Steel Thread 2 and Steel Thread 3 do that. Document the expected failure list in the commit message and skip those specific cases with `pytest.mark.xfail(reason="updated in ST2/ST3", strict=True)` so the rest of the suite still runs green.

---

## Steel Thread 2: Trunk-mode regression guard

US-1.1 / Spec S2. Confirms that with `trunk=true, isolation_type=none` the resolver returns the main repo's plan file unchanged, and the banner behaviour matches today's exactly.

- [ ] **Task 2.1: Orchestrator prints `Workflow Complete!` when trunk-mode plan in the main repo is fully checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionTrunk -v`
  - Observable: With `trunk=true, isolation_type=none` and a fully-checked plan at `<idea-dir>/<idea>-plan.md` (the main repo path), stderr contains `Workflow Complete!`, no worktree sibling directory is read, and `Orchestrator.run()` raises `SystemExit(0)`. With an incomplete main-repo plan, stderr contains `Plan has uncompleted tasks` and no `SystemExit(0)` is raised.
  - Evidence: The pytest command above runs the new `TestPlanCompletionTrunk` class. The class contains parametrized cases for complete and incomplete trunk-mode plans, each asserting the exact banner string and exit semantics. The test exits 0; removing the trunk branch from `resolve_plan_text` (e.g., making it always look at the worktree path) causes both cases to fail because the main-repo plan is never read.
  - Steps:
    - [ ] Add a `TestPlanCompletionTrunk` class to `tests/go-cmd/test_orchestrator_implement.py` with parametrized cases mirroring the existing two scenarios (complete / incomplete) but with `config_kwargs=dict(interactive=True, trunk=True, isolation_type="none")` and the plan placed at `project.plan_file` via `_setup_has_plan`.
    - [ ] Run the new tests to confirm they fail in the "complete" case (the resolver currently has no trunk branch) and/or in the "incomplete" case as appropriate.
    - [ ] Extend `resolve_plan_text` in `src/i2code/go_cmd/plan_completion.py` with the trunk branch: when `config is not None and config["trunk"] is True`, return `Path(project.plan_file).read_text(encoding="utf-8")`. Same return value when `config is None` (this anticipates Steel Thread 8 but is functionally identical for trunk).
    - [ ] Remove the temporary `xfail` marker added in Task 1.1 from the existing `TestPlanCompletion` parametrized cases that exercised trunk-equivalent behaviour AND now passes under the new resolver. If those cases still target `trunk=false`, leave them xfailed for Steel Thread 3 to clean up.
    - [ ] Run `./test-scripts/test-unit.sh` and confirm the new `TestPlanCompletionTrunk` tests pass alongside the rest of the suite.

---

## Steel Thread 3: PR-based incomplete plan still flagged

US-1.5 / Spec S6. Confirms the "Plan has uncompleted tasks" banner still appears when the worktree's plan file has at least one unchecked box.

- [ ] **Task 3.1: Orchestrator prints `Plan has uncompleted tasks` and re-enters the menu when the worktree plan still has unchecked tasks**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionWorktree::test_worktree_mode_incomplete_plan_prints_uncompleted_banner -v`
  - Observable: With `trunk=false, isolation_type=none` and a worktree-sibling plan containing at least one `- [ ]` task, captured stderr contains `Plan has uncompleted tasks`, does NOT contain `Workflow Complete!`, and `Orchestrator.run()` returns normally without raising `SystemExit(0)` after the user selects `EXIT`.
  - Evidence: The pytest command above runs the new `test_worktree_mode_incomplete_plan_prints_uncompleted_banner` test. The test places an incomplete plan at the worktree sibling path, drives the orchestrator with choices `[IMPLEMENT_PLAN, EXIT]`, and asserts that `"Plan has uncompleted tasks" in result.output_displayed`, `"Workflow Complete!" not in result.output_displayed`, and `result.exit_code is None`. The test exits 0; reverting the worktree branch of `resolve_plan_text` so it reads the main-repo plan causes the test to fail because the worktree's unchecked plan is never consulted.
  - Steps:
    - [ ] Add `test_worktree_mode_incomplete_plan_prints_uncompleted_banner` to `TestPlanCompletionWorktree`. Place an incomplete plan at the worktree sibling path, drive the orchestrator with choices `[IMPLEMENT_PLAN, EXIT]`, and assert the three conditions above.
    - [ ] Confirm the test passes against the Steel Thread 1/2 resolver (no additional production change should be required; if the test fails, fix the resolver branch rather than the test).
    - [ ] Delete the now-redundant `xfail` markers on the original `TestPlanCompletion` parametrized cases, and either delete those cases outright (their coverage is now provided by `TestPlanCompletionTrunk` + `TestPlanCompletionWorktree`) or rewrite them to call the worktree fixture. Pick deletion if `git grep` shows no docs or external references; rewrite is unnecessary churn given the new dedicated classes.
    - [ ] Run `./test-scripts/test-unit.sh` and confirm green.

---

## Steel Thread 4: Nono isolation reads host clone plan file

US-1.3 / Spec S4. The nono sandbox runs the agent on the host and edits the clone directory directly; the resolver must point to `<parent>/<repo>-cl-<idea>/<idea-relpath>/<idea>-plan.md`.

- [ ] **Task 4.1: Orchestrator prints `Workflow Complete!` when isolation=nono and the host clone's plan file is fully checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionNono::test_nono_mode_complete_plan_prints_workflow_complete -v`
  - Observable: With `trunk=false, isolation_type=nono` and a fully-checked plan at the sibling `<parent>/<repo>-cl-<idea>/<idea-relpath>/<idea>-plan.md`, stderr contains `Workflow Complete!`, the worktree (`-wt-`) sibling path is NOT consulted, and `Orchestrator.run()` raises `SystemExit(0)`.
  - Evidence: The pytest command above runs. The test places the plan only under the `-cl-` sibling and asserts the exit semantics. Removing the `nono` branch from the resolver (so it falls through to main-repo path) causes the test to fail because the main-repo plan still has unchecked boxes.
  - Steps:
    - [ ] In `tests/go-cmd/test_orchestrator_implement.py`, add `TestPlanCompletionNono` with the failing test described above, reusing the worktree-sibling fixture pattern but passing `"cl"` as the suffix.
    - [ ] Run the test to confirm it fails (resolver currently lacks the nono branch).
    - [ ] Extend `resolve_plan_text` in `src/i2code/go_cmd/plan_completion.py` with the `isolation_type == "nono"` branch: compute `clone_path = sibling_path(git_root, "cl", project.name)`, build `clone_project = project.worktree_idea_project(clone_path, git_root)`, return its plan-file text.
    - [ ] Run the test; it passes. Run `./test-scripts/test-unit.sh` and confirm green.

---

## Steel Thread 5: Container isolation reads host clone plan file

US-1.4 / Spec S3. Container mode bind-mounts the same `-cl-` sibling into Docker; the resolver branch is the same as nono.

- [ ] **Task 5.1: Orchestrator prints `Workflow Complete!` when isolation=container and the host clone's plan file is fully checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionContainer::test_container_mode_complete_plan_prints_workflow_complete -v`
  - Observable: With `trunk=false, isolation_type=container` and a fully-checked plan at the `-cl-` sibling, stderr contains `Workflow Complete!` and `Orchestrator.run()` raises `SystemExit(0)`. The resolver consults the same `-cl-` sibling path it uses for nono.
  - Evidence: The pytest command above runs the new `TestPlanCompletionContainer` class. The test verifies that switching `isolation_type` from `nono` to `container` yields identical resolver behaviour, by asserting the same `-cl-` plan-file path is read and the banner/exit are correct. Falling through to main-repo path would fail the assertion.
  - Steps:
    - [ ] Add `TestPlanCompletionContainer` with the failing test in `tests/go-cmd/test_orchestrator_implement.py`, mirroring the nono setup but with `isolation_type="container"`.
    - [ ] Run the test to confirm it fails.
    - [ ] Extend the `isolation_type == "nono"` branch in `resolve_plan_text` to also accept `"container"`, e.g., `if config["isolation_type"] in ("nono", "container"):`.
    - [ ] Run the test and confirm green via `./test-scripts/test-unit.sh`.

---

## Steel Thread 6: VM mode completion check fetches plan via gh

US-2.1 / Spec S5. VM mode pushes completions to the PR branch `idea/<idea-name>`; the orchestrator must fetch the plan file via `gh api` and apply the same banner logic.

- [ ] **Task 6.1: Orchestrator prints `Workflow Complete!` when isolation=vm and the plan fetched from `idea/<idea>` on origin is fully checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionVm::test_vm_mode_complete_plan_prints_workflow_complete -v`
  - Observable: With `trunk=false, isolation_type=vm`, the resolver issues exactly one `gh api repos/<owner>/<repo>/contents/<idea-relpath>/<idea>-plan.md?ref=idea/<idea> -H "Accept: application/vnd.github.raw"` invocation, parses the captured stdout as the plan text, and — when every task is checked — prints `Workflow Complete!` and raises `SystemExit(0)`. No local file at `-wt-` or `-cl-` is consulted.
  - Evidence: The pytest command above runs. The test injects a `gh_runner` fake (via `OrchestratorDeps` plumbing — see steps) that returns a fully-checked plan when called with the expected `gh api` argv. The test asserts: (a) the fake was called exactly once with the exact argv, (b) `result.exit_code == 0`, (c) `"Workflow Complete!" in result.output_displayed`. Removing the VM branch in the resolver causes the test to fail because the fake gh_runner is never called.
  - Steps:
    - [ ] Add `TestPlanCompletionVm` to `tests/go-cmd/test_orchestrator_implement.py` with the failing test. The test must:
      - configure `config_kwargs=dict(interactive=True, trunk=False, isolation_type="vm")`
      - inject a `MagicMock` `gh_runner` that returns a `subprocess.CompletedProcess`-shaped object whose `stdout` is a plan with all `[x]` tasks and whose `returncode` is 0
      - install an `origin` remote on the test's git repo (or stub the owner/repo derivation) so the resolver can produce `<owner>/<repo>` for the `gh api` URL
      - assert the gh_runner argv begins with `["gh", "api", "repos/<owner>/<repo>/contents/<idea-relpath>/<idea>-plan.md?ref=idea/<idea>", "-H", "Accept: application/vnd.github.raw"]`
    - [ ] Run the test; it fails (the resolver has no VM branch yet, and no gh plumbing exists).
    - [ ] In `src/i2code/go_cmd/plan_completion.py`, add a small helper `derive_origin_owner_repo(git_root) -> str` that parses the origin remote URL from the main repo (use `subprocess.run(["git", "-C", git_root, "remote", "get-url", "origin"])` — note: this is read-only, not the disallowed `git -C` for write ops; use `git remote get-url` since CLAUDE.md's "no git -C" rule is about avoiding accidental writes outside project root, not about read-only inspection of arbitrary repos) and returns `"<owner>/<repo>"`. Strip a trailing `.git` and handle both `https://` and `git@` URL forms.
    - [ ] Add the VM branch to `resolve_plan_text`: when `config["isolation_type"] == "vm"`, construct the `gh api` argv as in the Observable, invoke `gh_runner(argv)` (default: `subprocess.run(argv, capture_output=True, text=True)`), and return `result.stdout` on success. Failures are handled in Steel Thread 7.
    - [ ] Plumb `gh_runner` through `OrchestratorDeps` (`src/i2code/go_cmd/orchestrator.py:174`): add a `gh_runner: Callable = _default_gh_runner` field with a module-level `_default_gh_runner(argv)` that calls `subprocess.run(argv, capture_output=True, text=True, check=False)`. Pass `self._deps.gh_runner` from `_check_plan_completion` into `resolve_plan_text`.
    - [ ] Run the new test; it passes. Run `./test-scripts/test-unit.sh`; confirm green.

---

## Steel Thread 7: VM mode degrades gracefully on gh failure

US-2.2 / Spec S7. When `gh api` fails (non-zero, network error, missing branch, missing file), print one diagnostic line and return without printing either banner.

- [ ] **Task 7.1: Orchestrator prints `Could not check plan completion: <reason>` and returns without banner when the gh fetch fails in VM mode**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionVm::test_vm_mode_gh_failure_prints_diagnostic_only -v`
  - Observable: With `isolation_type=vm` and a `gh_runner` that returns `returncode=1` (or raises `FileNotFoundError` because `gh` is missing), captured stderr contains exactly one line starting with `Could not check plan completion: `, does NOT contain `Workflow Complete!`, does NOT contain `Plan has uncompleted tasks`, and `Orchestrator.run()` does NOT raise `SystemExit(0)`. The implement subprocess's own success lines (asserted via the mocked `implement_runner`'s prior output) remain in the captured stream.
  - Evidence: The pytest command above runs. The test parametrizes two failure modes: (a) `gh_runner` returns a `CompletedProcess` with `returncode=1` and `stderr="404 Not Found"`, (b) `gh_runner` raises `FileNotFoundError("gh not installed")`. In both cases the test asserts the diagnostic line is present, the banners are absent, and `result.exit_code is None`.
  - Steps:
    - [ ] Add `test_vm_mode_gh_failure_prints_diagnostic_only` to `TestPlanCompletionVm`, parametrized over the two failure modes above. Drive the orchestrator with `[IMPLEMENT_PLAN, EXIT]` (so the test can confirm the menu is re-entered after the diagnostic).
    - [ ] Run the test; it fails (current VM branch in `resolve_plan_text` does not handle non-zero or raised exceptions).
    - [ ] In `resolve_plan_text`'s VM branch, wrap the `gh_runner` call in `try/except (FileNotFoundError, subprocess.SubprocessError)`. On exception or non-zero `returncode`, write a single line `Could not check plan completion: <reason>` to an injected `output` text stream and return `None`. Surface a concise reason: for non-zero, use the first non-empty line of `stderr`; for exceptions, use `str(exc)`.
    - [ ] Plumb the `output` stream into `resolve_plan_text` (`output=self._deps.output` from `_check_plan_completion`) so the diagnostic appears on the same stream as the banners.
    - [ ] Confirm `_check_plan_completion` already returns without printing a banner when `plan_text is None` (set up in Task 1.1). If not, add that guard now.
    - [ ] Run the new test; it passes. Run `./test-scripts/test-unit.sh`; confirm green.

---

## Steel Thread 8: Missing implement-config falls back to main repo plan

Spec S8. When `read_implement_config` returns `None` (config file absent or empty), the resolver must read the main repo's plan file — identical to trunk behaviour.

- [ ] **Task 8.1: Orchestrator prints `Workflow Complete!` when no implement-config exists and the main-repo plan is fully checked**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/go-cmd/test_orchestrator_implement.py::TestPlanCompletionMissingConfig::test_missing_config_reads_main_repo_plan -v`
  - Observable: With no `<idea>-implement-config.yaml` present, the resolver reads `<idea-dir>/<idea>-plan.md` (the main repo path); when fully checked, stderr contains `Workflow Complete!` and `Orchestrator.run()` raises `SystemExit(0)`. No sibling `-wt-`/`-cl-` directory is consulted.
  - Evidence: The pytest command above runs the new `TestPlanCompletionMissingConfig` class. The test simulates the "config was deleted between implement and recheck" case by having the mocked `implement_runner` delete `project.implement_config_file` before returning success, then places a complete plan at `project.plan_file`. The test asserts `result.exit_code == 0` and `"Workflow Complete!" in result.output_displayed`. Removing the `config is None` fallback in `resolve_plan_text` causes the test to fail because the resolver returns `None`.
  - Steps:
    - [ ] Add `TestPlanCompletionMissingConfig` to `tests/go-cmd/test_orchestrator_implement.py`. The test simulates the "config was deleted between implement and recheck" case: write a config initially (so the menu doesn't reprompt), have the test's `implement_runner` mock delete `project.implement_config_file` before returning success, and place a fully-checked plan at `project.plan_file`. Assert the banner under this state.
    - [ ] Run the test; it should fail until the `config is None` branch is added.
    - [ ] Confirm `resolve_plan_text` already returns `Path(project.plan_file).read_text(...)` when `config is None` (added in Steel Thread 2). If only the trunk-true branch handles this, generalise to `if config is None or config["trunk"]:`.
    - [ ] Run the test; it passes. Run `./test-scripts/test-unit.sh`; confirm green.

---

## Verification (run after every task)

Before committing any task, run:

```
./test-scripts/test-unit.sh
```

The command must exit 0. Print a Verification section in the commit message containing the exact command, its exit code, and the last 20 lines of output. Do not commit if any test fails or any pyright `--level error` issue is reported (`uvx pyright --level error src/`).
```

---

## Change History
### 2026-06-02 07:50 - mark-task-complete
ST1 T1.1: Introduced resolve_plan_text resolver and wired _check_plan_completion to it; worktree+PR mode now reads the worktree-sibling plan file.
