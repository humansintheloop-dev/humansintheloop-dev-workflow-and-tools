# Discussion: Move config files inside uv app

## Classification

**Type: C. Platform/infrastructure capability**

**Rationale:** This simplifies the i2code CLI's internal plumbing by embedding config templates in the Python package, reducing required CLI arguments. It doesn't add new user-facing features or validate an architectural hypothesis — it improves developer ergonomics for existing commands.

## Questions and Answers

### Q1: Where should the config files live inside the package?

The idea originally said `src/config-files`, but hyphens aren't valid in Python package names.

**Answer:** `src/i2code/config_files/` — a Python subpackage inside i2code. Only the Claude-related files (CLAUDE.md, settings.local.json) should be moved there, not the git-hooks.

### Q2: Should --config-dir become optional or be removed entirely?

**Answer:** Optional with default. Keep `--config-dir` but default to `src/i2code/config_files` (via `importlib.resources`) when not specified. Preserves flexibility for overriding.

### Q3: Should project_dir also become optional?

**Answer:** Only for `setup` commands (`setup claude-files`, `setup update-project`) — these run in the target project, so defaulting to `.` makes sense. `improve update-claude-files` keeps `project_dir` required because it runs from the i2code repo and needs to be told the location of the external project to update from.

### Q4: How should the package locate its bundled config files?

**Answer:** Use `importlib.resources.files('i2code.config_files')`. This works correctly whether running from source (`uv run`) or installed as a package.

### Q5: How does SHA tracking work when installed as a published package?

When installed via editable install (`uv tool install -e .`), `importlib.resources` resolves to the source directory inside the git repo, so git SHA/diff operations work as they do today. For a published package (installed from PyPI), there's no git repo, so SHA tracking and diffs would fail.

**Answer:** Defer this concern for now. The existing silent fallback (full-template mode when no SHA is available) is acceptable. This can be revisited if/when i2code is published as a package.

### Q6: What happens to the original config-files/ directory?

**Answer:** Keep it for git-hooks only. The two Claude template files (CLAUDE.md, settings.local.json) are removed from it; the git-hooks subdirectory remains.

### Q7: Any additional requirements or concerns?

**Answer:** No. Ready to proceed to specification.
