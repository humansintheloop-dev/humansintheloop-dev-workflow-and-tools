Here is the implementation plan:

---

# Plan: Embed Claude Config Templates in i2code Package

## Idea Type

C. Platform/infrastructure capability

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Steel Thread 1: Package-Embedded Config Files with Default Discovery

This thread creates the `i2code.config_files` subpackage, wires `default_config_dir()` into all three CLI commands so `--config-dir` becomes optional, makes `project_dir` optional on `setup update-project`, and removes the original files from `config-files/`.

### Background

Currently three CLI commands require `--config-dir`:
- `setup claude-files` — `src/i2code/setup_cmd/cli.py:17` (`required=True`)
- `setup update-project` — `src/i2code/setup_cmd/cli.py:25` (`required=True`)
- `improve update-claude-files` — `src/i2code/improve/cli.py:48` (`required=True`)

The underlying functions (`setup_claude_files`, `update_project`, `update_claude_files`) accept `config_dir` as a plain string path — their signatures do not change. All changes are at the CLI layer.

Existing tests are in:
- `tests/setup-cmd/test_setup_cli.py` — tests `--config-dir` is required (lines 48-50, 82-84)
- `tests/setup-cmd/test_claude_files.py` — unit tests for `setup_claude_files()`
- `tests/setup-cmd/test_update_project.py` — unit tests for `update_project()`
- `tests/improve/test_improve_cli.py` — tests `--config-dir` is required (line 146-147)
- `tests/improve/test_update_claude_files.py` — unit tests for `update_claude_files()`

---

- [x] **Task 1.1: `default_config_dir()` returns the package directory path**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python -m pytest tests/config_files/ -v -m unit`
  - Observable: `default_config_dir()` returns a string path to a directory containing `CLAUDE.md` and `settings.local.json`
  - Evidence: Unit test imports `default_config_dir`, calls it, asserts the returned path is a directory containing both files
  - Steps:
    - [x] Create `tests/config_files/__init__.py`
    - [x] Create `tests/config_files/test_default_config_dir.py` with a test that imports `default_config_dir` from `i2code.config_files` and asserts: (1) return type is `str`, (2) the path is a directory, (3) it contains `CLAUDE.md`, (4) it contains `settings.local.json`
    - [x] Create `src/i2code/config_files/__init__.py` with `default_config_dir()` using `importlib.resources.files('i2code.config_files')`
    - [x] Copy `config-files/CLAUDE.md` to `src/i2code/config_files/CLAUDE.md`
    - [x] Copy `config-files/settings.local.json` to `src/i2code/config_files/settings.local.json`
    - [x] Verify tests pass

- [ ] **Task 1.2: `setup claude-files` works without `--config-dir`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python -m pytest tests/setup-cmd/test_setup_cli.py -v -m unit`
  - Observable: `i2code setup claude-files` succeeds without `--config-dir`, using the bundled templates; explicit `--config-dir` still overrides the default
  - Evidence: CLI tests verify (1) command succeeds without `--config-dir`, (2) `setup_claude_files` is called with the `default_config_dir()` path, (3) explicit `--config-dir` passes the provided path instead
  - Steps:
    - [ ] Update `tests/setup-cmd/test_setup_cli.py`: change `test_requires_config_dir_option` in `TestClaudeFilesCommandRegistered` to assert exit code 0 (no longer required). Add test that invocation without `--config-dir` passes `default_config_dir()` result to `setup_claude_files`. Add test that explicit `--config-dir` overrides the default.
    - [ ] Update `src/i2code/setup_cmd/cli.py:17`: change `--config-dir` from `required=True` to `default=None`. Add import of `default_config_dir` from `i2code.config_files`. In `claude_files_cmd`, resolve `config_dir = config_dir or default_config_dir()`
    - [ ] Verify tests pass

- [ ] **Task 1.3: `setup update-project` works without `--config-dir` and defaults `project_dir` to `.`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python -m pytest tests/setup-cmd/test_setup_cli.py -v -m unit`
  - Observable: `i2code setup update-project` succeeds without `--config-dir` (uses bundled default) and without `PROJECT_DIR` (defaults to `.`); explicit args still override defaults
  - Evidence: CLI tests verify (1) command succeeds with no args, (2) `update_project` receives `.` and `default_config_dir()` path, (3) explicit `PROJECT_DIR` and `--config-dir` override defaults
  - Steps:
    - [ ] Update `tests/setup-cmd/test_setup_cli.py`: change `test_requires_config_dir_option` in `TestUpdateProjectCommandRegistered` to assert exit code 0. Change `test_requires_project_dir_argument` to assert exit code 0 (default `.`). Add test for invocation without any args passing `.` and `default_config_dir()` to `update_project`. Add test for explicit args overriding defaults.
    - [ ] Update `src/i2code/setup_cmd/cli.py:24-25`: change `project_dir` from `@click.argument("project_dir")` to `@click.argument("project_dir", default=".")`. Change `--config-dir` from `required=True` to `default=None`. Resolve `config_dir = config_dir or default_config_dir()`
    - [ ] Verify tests pass

- [ ] **Task 1.4: `improve update-claude-files` works without `--config-dir`**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python -m pytest tests/improve/test_improve_cli.py -v -m unit`
  - Observable: `i2code improve update-claude-files PROJECT_DIR` succeeds without `--config-dir`, using bundled templates; `PROJECT_DIR` remains required; explicit `--config-dir` overrides
  - Evidence: CLI tests verify (1) command succeeds with only `PROJECT_DIR`, (2) `update_claude_files` receives `default_config_dir()` path, (3) `PROJECT_DIR` is still required, (4) explicit `--config-dir` overrides
  - Steps:
    - [ ] Update `tests/improve/test_improve_cli.py`: change `test_requires_config_dir_option` in `TestUpdateClaudeFilesCommandRegistered` to assert exit code 0. Add test for invocation without `--config-dir` passing `default_config_dir()` to `update_claude_files`. Update `_invoke_update` helper to support calls without `--config-dir`. Verify `PROJECT_DIR` still required (existing test).
    - [ ] Update `src/i2code/improve/cli.py:48`: change `--config-dir` from `required=True` to `default=None`. Add import of `default_config_dir` from `i2code.config_files`. In `update_claude_files_cmd`, resolve `config_dir = config_dir or default_config_dir()`
    - [ ] Verify tests pass

- [ ] **Task 1.5: Remove CLAUDE.md and settings.local.json from `config-files/`**
  - TaskType: REFACTOR
  - Entrypoint: `uv run python -m pytest tests/ -v -m unit`
  - Observable: No behavior change — all commands use bundled templates by default; `config-files/` retains only `git-hooks/`
  - Evidence: All existing unit tests pass; `config-files/CLAUDE.md` and `config-files/settings.local.json` no longer exist
  - Steps:
    - [ ] Delete `config-files/CLAUDE.md`
    - [ ] Delete `config-files/settings.local.json`
    - [ ] Verify all unit tests pass
    - [ ] Run `./test-scripts/test-end-to-end.sh` to confirm smoke tests pass

- [ ] **Task 1.6: Ensure non-Python files are included in wheel builds**
  - TaskType: INFRA
  - Entrypoint: `uv build`
  - Observable: The built wheel contains `i2code/config_files/CLAUDE.md` and `i2code/config_files/settings.local.json`
  - Evidence: `uv build` succeeds and inspecting the wheel (via `unzip -l`) shows both files present
  - Steps:
    - [ ] Check if `pyproject.toml` already includes non-Python files via `[tool.hatch.build]` configuration. If not, add the necessary configuration to include `*.md` and `*.json` files in `src/i2code/config_files/`
    - [ ] Run `uv build` and verify the wheel contents include both config files
    - [ ] Create `test-scripts/test-wheel-contents.sh` that builds the wheel and asserts both config files are present
    - [ ] Add `test-scripts/test-wheel-contents.sh` to `test-scripts/test-end-to-end.sh`
