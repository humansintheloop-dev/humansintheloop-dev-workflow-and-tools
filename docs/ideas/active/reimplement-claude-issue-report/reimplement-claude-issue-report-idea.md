## Reimplement claude-issue-report

### Currently

* Issue creation is a slash command `claude-code-plugins/idea-to-code/commands/claude-issue-report.md`
* Claude directly writes the issue file to `.hitl/issues/active/`
* A PostToolUse hook (`issue-session-tagger.js`) tags the file with the session ID after the Write tool fires

### Goal

Re-implement as a **skill + CLI subcommand** following the project's established pattern where skills delegate deterministic file I/O to `i2code` subcommands.

### Key Decisions

* **Skill**: `claude-issue-report` (user-invokable, also auto-suggested by Claude on detected mistakes)
* **CLI**: New `i2code issue create` subcommand under a new `issue` command group
* **Data flow**: Skill pipes all fields as JSON on stdin → CLI parses and assembles the markdown file
* **Session ID**: A PreToolUse hook detects `i2code issue create` and appends `--session-id <id>` from the hook payload
* **Target directory**: CLI auto-discovers `.hitl/issues/active/` from git root
* **Output**: CLI prints the absolute path to the created file
* **File format**: Unchanged
* **Migration**: Delete the slash command and the old PostToolUse hook; replace with new skill and PreToolUse hook

### Components to Create/Modify

1. **New**: `src/i2code/issue/` — CLI module with `create` subcommand
2. **New**: `claude-code-plugins/idea-to-code/skills/claude-issue-report/SKILL.md` — skill definition
3. **New**: PreToolUse hook for session ID injection
4. **Delete**: `claude-code-plugins/idea-to-code/commands/claude-issue-report.md` — old slash command
5. **Delete**: `claude-code-plugins/idea-to-code/hooks/issue-session-tagger.js` — old PostToolUse hook
6. **Modify**: `src/i2code/cli.py` — register new `issue` command group
7. **Modify**: `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json` — update skills and hooks
