Move the Claude config template files (CLAUDE.md, settings.local.json) from the top-level config-files/ directory into the i2code Python package at src/i2code/config_files/.

## Motivation

* i2code subcommands that copy/merge these into project files no longer need to be told where the source templates are — they can discover them via `importlib.resources`.
* `--config-dir` becomes optional (with the package location as default) rather than required.
* `setup` commands (`setup claude-files`, `setup update-project`) can default `project_dir` to `.` since they run in the target project.

## Scope

* Only CLAUDE.md and settings.local.json move into the package.
* The git-hooks files stay in config-files/git-hooks/ (config-files/ directory is kept for git-hooks only).
* `improve update-claude-files` keeps its `project_dir` argument required — it runs from the i2code repo and needs the external project path.

## Discovery mechanism

Use `importlib.resources.files('i2code.config_files')` to locate bundled config files. This works whether running from source (`uv run`) or installed as a package.
