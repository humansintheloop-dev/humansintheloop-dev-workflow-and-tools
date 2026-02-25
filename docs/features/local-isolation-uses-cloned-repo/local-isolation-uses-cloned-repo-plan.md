Now I have all the context I need. Let me generate the plan.

# Plan: Local Isolation Uses Cloned Repo

## Idea Type: C — Platform/infrastructure capability

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

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Overview

Currently, `IsolateMode` runs the isolarium subprocess in a git worktree. Worktrees share the `.git` directory with the main repo, allowing the agent to modify the main repo's git state (lock files, index, refs). This feature replaces the worktree as isolarium's working directory with a shallow clone — a fully independent git repo with its own `.git` directory that provides true filesystem and git-level security isolation.

**Key changes:**

1. After scaffolding completes in the worktree, `IsolateMode` creates a shallow clone of the worktree at `<repo>-cl-<idea-name>` (sibling directory)
2. The clone's `origin` remote is reconfigured to point to the GitHub remote URL (not the local worktree path)
3. Isolarium runs in the clone instead of the worktree
4. On re-runs, if the clone already exists, `ImplementCommand` skips worktree creation, scaffolding, and cloning — running isolarium directly in the existing clone

**Scope:** `IsolateMode` only. `WorktreeMode` and `TrunkMode` are unchanged.

**Key files to modify:**

- `src/i2code/implement/isolate_mode.py` — add `clone_creator` dependency, use clone as isolarium `cwd`
- `src/i2code/implement/git_repository.py` — add `origin_url` property
- `src/i2code/implement/mode_factory.py` — wire `RepoCloner` into `IsolateMode`
- `src/i2code/implement/implement_command.py` — add re-run short-circuit when clone exists

**New files:**

- `src/i2code/implement/repo_cloner.py` — `RepoCloner` class and `clone_path_for()` function
- `tests/implement/fake_repo_cloner.py` — test double for `RepoCloner`
- `tests/implement/test_repo_cloner.py` — tests for clone creation

## Steel Thread 1: First Run — Clone Creation and Isolarium Runs in Clone

Implements Scenario 1 from the specification: no clone exists yet. The full flow is: create worktree → scaffold → shallow clone worktree → reconfigure clone's origin → run isolarium in clone.

Also covers Scenario 3 (worktree exists with scaffolding guard, no clone) — the existing scaffolding guard prevents re-scaffolding, and clone creation proceeds normally from the already-scaffolded worktree.

Use TDD for all tasks.

- [x] **Task 1.1: IsolateMode runs isolarium in clone directory after scaffolding**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest -m unit tests/implement/test_isolate_mode.py`
  - Observable: After scaffolding succeeds, `IsolateMode.execute()` calls `clone_creator.create_clone()` with the worktree path, idea name, and origin URL, then runs the isolarium subprocess with `cwd` set to the returned clone path (not the worktree path)
  - Evidence: Unit tests using `FakeRepoCloner` verify: (1) `create_clone()` is called with `(worktree_path, idea_name, origin_url)`; (2) isolarium subprocess `cwd` is the clone path returned by `create_clone()`; (3) when scaffolding fails, `create_clone()` is never called
  - Steps:
    - [x] Add `origin_url` property to `src/i2code/implement/git_repository.py:GitRepository` — returns `self._repo.remotes.origin.url`
    - [x] Add `origin_url` property (default `"https://github.com/test/repo.git"`) and `set_origin_url()` method to `tests/implement/fake_git_repository.py:FakeGitRepository`
    - [x] Create `src/i2code/implement/repo_cloner.py` with: (a) module-level function `clone_path_for(repo_root, idea_name)` that returns `os.path.join(parent_dir, f"{basename}-cl-{idea_name}")`; (b) `RepoCloner` class with method `create_clone(source_path, idea_name, origin_url)` that raises `NotImplementedError`
    - [x] Create `tests/implement/fake_repo_cloner.py` with `FakeRepoCloner` that records calls and returns a configurable clone path
    - [x] Add `clone_creator` parameter to `IsolateMode.__init__()` in `src/i2code/implement/isolate_mode.py`
    - [x] Modify `IsolateMode.execute()`: after scaffolding, call `self._clone_creator.create_clone(source_path=self._git_repo.working_tree_dir, idea_name=self._project.name, origin_url=self._git_repo.origin_url)`, use the returned clone path as the `cwd` argument to `self._subprocess_runner.run()`
    - [x] Update `src/i2code/implement/mode_factory.py:ModeFactory.make_isolate_mode()` to instantiate `RepoCloner()` and pass it as `clone_creator` to `IsolateMode`
    - [x] Write new unit tests in `tests/implement/test_isolate_mode.py`: (a) verify `create_clone()` called with correct args after scaffolding; (b) verify subprocess `cwd` is clone path; (c) verify `create_clone()` not called when scaffolding fails
    - [x] Update existing unit tests in `tests/implement/test_isolate_mode.py` to pass `clone_creator=FakeRepoCloner()` to `_make_mode()` helper

- [x] **Task 1.2: RepoCloner creates shallow clone with GitHub origin**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest -m unit tests/implement/test_repo_cloner.py`
  - Observable: `RepoCloner.create_clone()` creates a shallow git clone at `<parent>/<repo-basename>-cl-<idea_name>`, with the `origin` remote URL set to the provided GitHub URL (not the source worktree path), an independent `.git` directory (a directory, not a worktree pointer file), and a depth of 1. When the clone directory already exists, it returns the path without re-cloning.
  - Evidence: Tests create a real git repo in `tmp_path`, call `create_clone()`, and verify: (1) clone directory exists at expected sibling path; (2) `git remote get-url origin` in clone returns the provided GitHub URL; (3) clone's `.git` is a directory; (4) clone is shallow (single commit); (5) `create_clone()` returns existing path when clone already exists
  - Steps:
    - [x] Implement `RepoCloner.create_clone()` in `src/i2code/implement/repo_cloner.py`: compute clone path via `clone_path_for()`, if clone dir exists return path early, otherwise run `git clone --depth 1 <source> <clone>`, then run `git remote set-url origin <github_url>` in the clone, return clone path
    - [x] Create `tests/implement/test_repo_cloner.py` — helper to set up a bare-minimum git repo in `tmp_path`
    - [x] Test: clone directory is created at expected sibling path (e.g., `<parent>/<name>-cl-<idea>`)
    - [x] Test: clone's `origin` URL is the provided GitHub URL (not the source worktree path)
    - [x] Test: clone has independent `.git` directory (is a directory, not a file)
    - [x] Test: clone is shallow (verify with `git rev-list --count HEAD` returning 1)
    - [x] Test: `create_clone()` returns existing path when clone directory already exists (idempotent)
    - [x] Test: `clone_path_for()` computes correct path

- [ ] **Task 1.3: End-to-end integration test verifies isolarium runs in clone**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest -m integration_gh tests/implement/test_isolate_mode_integration.py`
  - Observable: When running `i2code implement --isolate`, the fake isolarium's captured `cwd` is the clone path (contains `-cl-`), the clone's `origin` remote URL matches the GitHub remote, and the clone has an independent `.git` directory. Both worktree (`-wt-`) and clone (`-cl-`) directories exist on disk. Main repo branch is unchanged.
  - Evidence: Integration test creates a GitHub repo, runs the full isolate flow with a fake isolarium, and asserts: (1) isolarium `cwd` contains `-cl-` (clone path); (2) clone's `origin` URL matches GitHub; (3) clone's `.git` is a directory; (4) worktree directory exists; (5) main repo branch unchanged
  - Steps:
    - [ ] Compute expected clone path in test using `-cl-` convention (add `_clone_path_for()` helper alongside existing `_worktree_path_for()`)
    - [ ] Update `_assert_isolarium_ran_in_worktree` (rename to `_assert_isolarium_ran_in_clone`) to verify `cwd` is the clone path
    - [ ] Add `_assert_clone_origin_is_github()`: verify clone's `origin` URL matches the GitHub repo URL (using `git -C <clone> remote get-url origin`)
    - [ ] Add `_assert_clone_has_independent_git()`: verify clone's `.git` is a directory (not a file pointing to main repo's `.git`)
    - [ ] Retain `_assert_worktree_created()` — worktree should still exist as scaffolding staging area
    - [ ] Retain `_assert_main_branch_unchanged()` — main repo is protected
    - [ ] Add clone directory to fixture teardown cleanup (`shutil.rmtree`)

## Steel Thread 2: Re-run Reuses Existing Clone

Implements Scenario 2 from the specification: the clone directory already exists from a previous run. `ImplementCommand` detects the existing clone, skips worktree creation, scaffolding, and cloning, and runs isolarium directly in the existing clone.

Use TDD for all tasks.

- [ ] **Task 2.1: ImplementCommand skips worktree and scaffolding when clone exists**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest -m unit tests/implement/test_implement_command.py`
  - Observable: When the clone directory (`<repo>-cl-<idea>`) already exists, `ImplementCommand._isolate_mode()` does not call `ensure_worktree()` or `ensure_idea_branch()`, does not run scaffolding, and runs isolarium with `cwd` set to the existing clone path
  - Evidence: Unit test creates a pre-existing clone directory (using `tmp_path`), invokes the isolate mode flow, and verifies: (1) `ensure_worktree` was NOT called on the fake `git_repo`; (2) `ensure_idea_branch` was NOT called; (3) isolarium subprocess `cwd` is the pre-existing clone path
  - Steps:
    - [ ] Extract `launch()` method from `IsolateMode.execute()` in `src/i2code/implement/isolate_mode.py` — `launch(options)` builds the isolarium command and runs the subprocess using `self._git_repo.working_tree_dir` as `cwd`. Update `execute()` to use `launch()` internally (passing clone path as needed). Existing tests must continue to pass.
    - [ ] In `src/i2code/implement/implement_command.py:ImplementCommand._isolate_mode()`: at the top, compute the clone path via `clone_path_for(self.git_repo.working_tree_dir, self.project.name)`; if the clone directory exists, create a `GitRepository` wrapping the clone (with `main_repo_dir=self.git_repo.working_tree_dir`), compute the clone's `IdeaProject` via `worktree_idea_project()`, create `IsolateMode` via `ModeFactory`, call `launch()`, and `sys.exit(returncode)` — skipping worktree creation and scaffolding entirely
    - [ ] Write unit tests in `tests/implement/test_implement_command.py`: (a) when clone dir exists, `ensure_worktree` and `ensure_idea_branch` are NOT called, isolarium runs in clone; (b) when clone dir does NOT exist, the normal worktree → scaffolding → clone flow proceeds as before
    - [ ] Verify existing tests still pass (the non-isolate paths are unchanged)

---

## Change History
### 2026-02-26 08:15 - mark-task-complete
All 7 tests pass verifying: clone at expected sibling path, origin URL is GitHub URL, independent .git directory, shallow clone (depth 1), idempotent re-run, and clone_path_for computes correct path
