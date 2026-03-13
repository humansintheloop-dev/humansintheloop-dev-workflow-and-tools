Implement an i2code status command

A command that shows the current state of development across all active ideas.

## Global summary (default, no arguments)

Shows a rich-formatted table of all active ideas (those not in `complete` state) with:

* Lifecycle state (has_idea, has_spec, has_plan, complete)
* Worktree status (exists or not)
* PR status (open/draft/merged/closed + CI passing/failing/pending)
* Plan progress (e.g., 3/7 tasks done)
* Whether the current local branch is behind its remote tracking branch

Use `--all` flag to include completed ideas.

## Single-idea drill-down (`i2code status <idea-name>`)

Shows the same information as the summary row, but in a more readable non-table format.

## Design decisions

* Online by default — fetches from origin and queries GitHub API for PR/CI status
* Convention-based detection — only finds worktrees/branches/PRs following the `idea/<name>/...` naming pattern
* Rich colored terminal output (using `rich` library)
* Python Click command (not shell script)
