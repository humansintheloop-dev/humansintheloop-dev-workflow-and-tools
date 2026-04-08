# Platform Capability Specification: Embed Claude Config Templates in i2code Package

## Purpose and Context

Three i2code CLI commands currently require the user to pass `--config-dir` pointing to the top-level `config-files/` directory every time they are invoked. This is friction that can be eliminated by moving the two Claude template files (CLAUDE.md, settings.local.json) into the `i2code` Python package itself, where they can be discovered automatically via `importlib.resources`.

### Current state

The `config-files/` directory at the repository root contains:

```
config-files/
  CLAUDE.md
  settings.local.json
  git-hooks/
    .pre-commit-config.yaml
    precommit.sh
    pre-commit-install.sh
```

Three commands require `--config-dir` as a **required** option:

| Command | Additional args | Purpose |
|---|---|---|
| `i2code setup claude-files` | (none) | Copy CLAUDE.md and settings.local.json into a target project |
| `i2code setup update-project` | `PROJECT_DIR` (required) | Push template updates into a project using git SHA diffs |
| `i2code improve update-claude-files` | `PROJECT_DIR` (required) | Review a project's Claude files and update the templates |

### Target state

- CLAUDE.md and settings.local.json move to `src/i2code/config_files/`
- `--config-dir` becomes optional, defaulting to the package location
- `setup` commands default `project_dir` to `.`
- `improve update-claude-files` keeps `project_dir` required
- `config-files/` at repo root is retained for git-hooks only

## Consumers

| Consumer | How they use config templates |
|---|---|
| Developer setting up a new project | Runs `i2code setup claude-files` to copy templates into their project |
| Developer syncing template updates | Runs `i2code setup update-project` to pull latest template changes |
| i2code maintainer | Runs `i2code improve update-claude-files` to backport project customizations into templates |

## Capabilities and Behaviors

### C1: Package-embedded config files

Create a Python subpackage `i2code.config_files` containing:

```
src/i2code/config_files/
  __init__.py
  CLAUDE.md
  settings.local.json
```

The `__init__.py` must expose a single function:

```python
def default_config_dir() -> str:
    """Return the filesystem path to the bundled config files directory."""
```

This function uses `importlib.resources.files('i2code.config_files')` and returns the result as a string path.

### C2: Optional --config-dir with package default

All three commands that accept `--config-dir` change it from `required=True` to `required=False, default=None`. When `None`, the command calls `default_config_dir()` to resolve the path.

**Before:**
```
i2code setup claude-files --config-dir /path/to/config-files
```

**After (both valid):**
```
i2code setup claude-files
i2code setup claude-files --config-dir /custom/path
```

When `--config-dir` is explicitly provided, it takes precedence over the package default.

### C3: Optional project_dir for setup commands

The two `setup` commands change `project_dir` from a required argument to an optional argument defaulting to `.`:

| Command | Before | After |
|---|---|---|
| `setup claude-files` | No project_dir arg (hardcoded to `.`) | No change needed — already uses `.` |
| `setup update-project` | `PROJECT_DIR` required argument | `PROJECT_DIR` optional, defaults to `.` |

`improve update-claude-files` keeps `PROJECT_DIR` as a required argument — it runs from the i2code repository and must be told which external project to read from.

### C4: Remove Claude files from config-files/

After moving CLAUDE.md and settings.local.json into the package, remove them from `config-files/`. The directory is retained with only the `git-hooks/` subdirectory:

```
config-files/
  git-hooks/
    .pre-commit-config.yaml
    precommit.sh
    pre-commit-install.sh
```

## High-Level APIs and Contracts

### New module: `i2code.config_files`

**`i2code/config_files/__init__.py`**

```python
from importlib.resources import files

def default_config_dir() -> str:
    return str(files("i2code.config_files"))
```

### CLI changes

**`i2code/setup_cmd/cli.py`** — `--config-dir` becomes optional on both commands; `project_dir` becomes optional on `update-project`:

```python
@setup_group.command("claude-files")
@click.option("--config-dir", default=None, help="Path to the config-files directory. Defaults to bundled templates.")
def claude_files_cmd(config_dir):
    if config_dir is None:
        config_dir = default_config_dir()
    setup_claude_files(config_dir)

@setup_group.command("update-project")
@click.argument("project_dir", default=".")
@click.option("--config-dir", default=None, help="Path to the config-files directory. Defaults to bundled templates.")
def update_project_cmd(project_dir, config_dir):
    if config_dir is None:
        config_dir = default_config_dir()
    ...
```

**`i2code/improve/cli.py`** — `--config-dir` becomes optional; `project_dir` stays required:

```python
@improve.command("update-claude-files")
@click.argument("project_dir")
@click.option("--config-dir", default=None, help="Path to the config-files directory. Defaults to bundled templates.")
def update_claude_files_cmd(project_dir, config_dir):
    if config_dir is None:
        config_dir = default_config_dir()
    ...
```

### Internal functions — no signature changes

The underlying functions (`setup_claude_files`, `update_project`, `update_claude_files`) accept `config_dir` as a string path. Their signatures and behavior do not change. The CLI layer resolves the default before calling them.

## Non-Functional Requirements

- **Backward compatibility:** Explicitly passing `--config-dir` must continue to work identically. No existing invocations break.
- **Git SHA tracking:** The `update-project` command's SHA/diff mechanism (`_get_repo_root`, `_get_current_sha`, `_get_config_diff`) continues to work for editable installs. For published package installs (no git repo), the existing silent fallback to full-template mode is acceptable.
- **Package build:** `src/i2code/config_files/` must be included in wheel builds. The non-Python files (CLAUDE.md, settings.local.json) must be included as package data.

## Scenarios and Workflows

### Scenario 1 (primary): Setup a new project with default config

A developer `cd`s into their new project directory and runs:

```
i2code setup claude-files
```

The command discovers the bundled CLAUDE.md and settings.local.json via `importlib.resources`, copies CLAUDE.md to `.` and settings.local.json to `.claude/`.

### Scenario 2: Setup with custom config directory

A developer has a custom set of templates and runs:

```
i2code setup claude-files --config-dir /path/to/custom/templates
```

The command uses the explicitly provided path, ignoring the package default.

### Scenario 3: Push template updates to a project (default project dir)

A developer is inside their project directory and runs:

```
i2code setup update-project
```

Both `project_dir` (`.`) and `config_dir` (package default) are resolved automatically. The command extracts the previous SHA from `./CLAUDE.md`, computes diffs, and invokes Claude.

### Scenario 4: Update config templates from a project

A maintainer is inside the i2code repository and runs:

```
i2code improve update-claude-files /path/to/project
```

`project_dir` is required and explicitly provided. `config_dir` defaults to the bundled templates. The command reads the project's Claude files and invokes Claude to update the templates.

## Constraints and Assumptions

- The i2code package is primarily used via editable installs (`uv tool install -e .`). Published package support for SHA tracking is deferred.
- Non-Python files (CLAUDE.md, settings.local.json) in `src/i2code/config_files/` must be included as package data. This may require a `py.typed` marker or explicit inclusion in `pyproject.toml` via `[tool.hatch.build.targets.wheel.force-include]` or similar.
- The git-hooks files are not moved and remain at `config-files/git-hooks/`.

## Acceptance Criteria

1. `i2code setup claude-files` works without `--config-dir` and copies the bundled CLAUDE.md and settings.local.json into the current directory.
2. `i2code setup update-project` works without `--config-dir` or `project_dir`, operating on `.` with bundled templates.
3. `i2code improve update-claude-files /path/to/project` works without `--config-dir`, using bundled templates.
4. All three commands still accept `--config-dir` to override the default.
5. `config-files/` at repo root contains only the `git-hooks/` subdirectory.
6. Existing tests are updated and pass.
7. `importlib.resources.files('i2code.config_files')` resolves correctly for both editable and built-wheel installs.
