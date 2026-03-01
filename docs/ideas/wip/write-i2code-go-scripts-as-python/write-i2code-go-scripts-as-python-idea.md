Incrementally migrate all `i2code` bash scripts (and their tests) from bash to Python, fully eliminating bash from the codebase.

Use the command/assembler/strategy patterns already established by the `implement` command. Each workflow step becomes a standalone, tested Python function/class callable both from the `i2code go` orchestrator and from direct subcommands.

Migration order:
1. `idea-to-code.sh` (orchestrator) — calls remaining bash scripts via `script_runner.py` during transition
2. Workflow scripts in order: brainstorm, make-spec, revise-spec, make-plan, revise-plan, list-plugin-skills
3. Utility scripts: design, analyze-sessions, summary-reports, review-issues, claude-files management
4. Cleanup: delete `scripts/`, `script_command.py`, `script_runner.py`, and bash test scripts

Key decisions:
- Simple `input()` menus (no new dependencies)
- `string.Template` for prompt templates (compatible with existing `$VARIABLE` syntax)
- Extend `IdeaProject` for path derivation and validation (replaces `_helper.sh`)
- Reuse `ClaudeRunner` for Claude invocation
- TDD with pytest; bash tests deleted per-script as each is migrated
- No user-facing behavior change — CLI commands, arguments, and output stay the same
