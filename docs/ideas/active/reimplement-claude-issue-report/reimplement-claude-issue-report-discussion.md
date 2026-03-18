# Discussion: Reimplement claude-issue-report

## Classification

**Type: C. Platform/infrastructure capability**

**Rationale:** This is an internal tooling refactoring — moving issue creation from a slash command (where Claude directly writes files) to a skill + CLI subcommand pattern. It aligns with the existing architectural convention where skills delegate deterministic file I/O to `i2code` subcommands. No new user-facing functionality is being added; the capability and file format are unchanged.

## Questions & Answers

### Q1: Data passing — What data should the skill pass to `i2code issue create`?

**Answer: Structured arguments via JSON on stdin.** The skill pipes all fields as a JSON object to the CLI via stdin. The CLI parses the JSON and assembles the markdown file. This avoids shell quoting issues for all fields.

### Q2: Context argument — How should conversation context be passed?

**Answer: Included in the stdin JSON.** All fields including the context block are part of the JSON object piped to stdin. The file format is unchanged — all sections (5 whys, context, suggested improvement) are preserved.

### Q3: Migration — Should the existing slash command be kept alongside the new skill?

**Answer: Remove immediately.** The slash command (`commands/claude-issue-report.md`) is deleted as part of this work. The skill fully replaces it with no transition period.

### Q4: CLI location — Where should the new command live?

**Answer: New `issue` command group.** Add `i2code issue` as a new top-level command group with `create` as its first subcommand. Leaves room for future subcommands (list, resolve, etc.).

### Q5: Session ID — How should the session ID be captured?

**Answer: PreToolUse hook appends a CLI flag.** The skill doesn't have access to the session ID directly. A PreToolUse hook detects `i2code issue create` in the Bash command and appends `--session-id <actual_session_id>` from the hook payload. The CLI accepts this as an optional flag and writes it into the file.

This replaces the current PostToolUse `issue-session-tagger.js` hook which triggers on Write tool operations (which won't fire when the CLI writes the file via Bash).

### Q6: Target directory — How does the CLI find where to write?

**Answer: Auto-discover.** The CLI finds the project root (git root or cwd) and uses `.hitl/issues/active/` relative to it. Matches how `i2code tracking` already works.

### Q7: CLI output — What should `i2code issue create` print on success?

**Answer: Absolute file path only.** Print just the path to the created file. The skill relays this to the user. Clean for scripting.

### Q8: Hook cleanup — What happens to the existing `issue-session-tagger.js`?

**Answer: Replace entirely.** Delete the old PostToolUse hook (`issue-session-tagger.js`) and create the new PreToolUse hook. One hook, one mechanism.

### Q9: Skill naming — Should the skill be renamed?

**Answer: Keep `claude-issue-report`.** Users who already know the name don't need to relearn it.

### Q10: Invocation mode — User-only or also auto-triggered?

**Answer: Both.** The skill is user-invokable (user types `/claude-issue-report`), AND the skill description includes guidance for Claude to proactively suggest filing an issue when it detects it made a mistake. Claude suggests and waits for user approval before filing — it does not auto-file.

### Q11: JSON input format — How should the 5 whys analysis be structured?

**Answer: Single text block.** One `analysis` field containing the full 5 whys markdown. The skill formats the analysis however it sees fit; the CLI just places it in the template section. Simpler and doesn't constrain the skill's output.

## Summary of JSON Input Schema

The CLI expects a JSON object on stdin with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | User's description of the issue |
| `category` | string | One of: `rule-violation`, `improvement`, `confusion` |
| `analysis` | string | Full 5 whys analysis as markdown |
| `context` | string | Last 5 message exchanges as markdown |
| `suggestion` | string | Suggested improvement to prevent recurrence |

Plus the `--session-id` flag appended by the PreToolUse hook.
