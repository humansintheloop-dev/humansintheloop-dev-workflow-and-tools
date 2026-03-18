# Platform Capability Specification: Reimplement claude-issue-report

## Purpose and Context

The `/claude-issue-report` slash command (`claude-code-plugins/idea-to-code/commands/claude-issue-report.md`) allows users to capture mistakes and improvement opportunities as structured issue reports with 5 whys analysis. Currently, the slash command instructs Claude to directly write the issue file using the Write tool, and a PostToolUse hook (`hooks/issue-session-tagger.js`) patches in the session ID after the write.

This work re-implements the capability as a **skill + CLI subcommand** pair, following the project's established pattern where skills handle AI reasoning and delegate deterministic file I/O to `i2code` subcommands. The file format and user-facing behavior are unchanged.

## Consumers

| Consumer | How it uses the capability |
|----------|---------------------------|
| Claude Code user | Invokes `/claude-issue-report` to file an issue about a mistake or improvement opportunity |
| Claude (auto-suggest) | Proactively suggests filing an issue when it detects it made a mistake; waits for user approval before filing |
| `i2code improve review-issues` | Reads issue files from `.hitl/issues/active/` for triage — no changes needed, file format is unchanged |

## Capabilities and Behaviors

### C1: Skill — `claude-issue-report`

The skill replaces the existing slash command. It is a user-invokable skill at `claude-code-plugins/idea-to-code/skills/claude-issue-report/SKILL.md`.

**SKILL.md frontmatter:**

```yaml
---
name: claude-issue-report
description: Capture mistake or improvement opportunity with 5 whys analysis
user-invokable: true
---
```

**Skill responsibilities** (AI-side reasoning, same as current slash command):

1. Extract the description from the user's `/claude-issue-report` invocation
2. Identify current persona/role
3. Perform 5 whys root cause analysis
4. Extract last 5 message exchanges from the conversation
5. Suggest an actionable improvement the **user** can take (not instructions for Claude)
6. Pipe all fields as JSON to `i2code issue create` via the Bash tool
7. Report the created file path back to the user: "Report captured: [path]"

**Auto-suggest behavior:** The skill description includes guidance for Claude to proactively suggest filing an issue when it detects it made a mistake. Claude says something like "I made a mistake here — would you like me to file an issue report?" and waits for explicit user approval before invoking the skill. Claude never auto-files.

**Post-filing behavior** (carried over from current command):

1. After filing, assess current state — if work is functional, don't undo it
2. Only "fix" if explicitly asked or if the current state is broken
3. Ask for clarification if unsure whether to continue, undo, or just document

### C2: CLI — `i2code issue create`

A new Click command group `issue` is added to `src/i2code/cli.py` with `create` as its first subcommand.

**Module location:** `src/i2code/issue/` with:
- `src/i2code/issue/__init__.py`
- `src/i2code/issue/cli.py` — Click group and `create` command
- `src/i2code/issue/create.py` — issue creation logic

**Command signature:**

```
i2code issue create [--session-id TEXT]
```

Reads JSON from stdin. The `--session-id` flag is optional and is appended by the PreToolUse hook (not passed by the skill).

**JSON input schema (stdin):**

```json
{
  "description": "User's description of the issue",
  "category": "rule-violation",
  "analysis": "## 5 Whys Analysis\n\n1. **Why did this happen?** ...",
  "context": "## Context (Last 5 Messages)\n\n...",
  "suggestion": "Add a rule to CLAUDE.md that..."
}
```

All fields are required strings. The `category` field accepts one of: `rule-violation`, `improvement`, `confusion`.

**File generation:**

The CLI assembles the markdown file using this template:

```markdown
---
id: YYYY-MM-DD-HH-MM-SS
created: ISO8601 timestamp
status: active
category: {category}
claude_session_id: {session_id or "unknown"}
---

# {description}

{analysis}

{context}

## Suggested improvement

{suggestion}

## Resolution

[Empty - filled when resolved]
```

The `id` and `created` fields are derived from the current timestamp at creation time. The `analysis` and `context` fields are inserted verbatim — the skill is responsible for formatting them with the appropriate markdown headers.

**Target directory discovery:**

The CLI finds the project root using `Path.cwd()` (matching the pattern in `src/i2code/idea/resolver.py:28`) and writes to `.hitl/issues/active/` relative to it. The directory must already exist (created by `i2code tracking setup`).

If `.hitl/issues/active/` does not exist, the CLI prints an error to stderr and exits with code 1.

**Output on success:**

Prints the absolute path to the created file on stdout, e.g.:

```
/Users/name/project/.hitl/issues/active/2026-03-18-14-30-00.md
```

**File naming:**

`YYYY-MM-DD-HH-MM-SS.md` using the same timestamp as the `id` field. This matches the current naming convention.

### C3: PreToolUse Hook — Session ID Injection

A new PreToolUse hook replaces the existing PostToolUse `issue-session-tagger.js`.

**Hook location:** `claude-code-plugins/idea-to-code/hooks/issue-session-injector.js`

**Trigger:** PreToolUse events where `tool_name === 'Bash'` and `tool_input.command` contains `i2code issue create`.

**Behavior:**

1. Receive the hook payload including `session_id` and `tool_input.command`
2. If `session_id` is present and the command contains `i2code issue create`:
   - Append ` --session-id <session_id>` to the command string
   - Output the modified tool input as JSON on stdout (so Claude Code applies it)
3. If `session_id` is absent or the command doesn't match, exit 0 (pass through)

**Hook registration in `plugin.json`:**

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node ${CLAUDE_PLUGIN_ROOT}/hooks/issue-session-injector.js"
    }
  ]
}
```

This is added to the existing `PreToolUse` array. The existing `enforce-bash-conventions.js` entry already uses a `"matcher": "Bash"` block; the new hook is a separate entry in the same array.

## High-Level APIs, Contracts, and Integration Points

### Skill → CLI Contract

The skill invokes the CLI via:

```bash
echo '<json>' | i2code issue create
```

The PreToolUse hook transparently modifies this to:

```bash
echo '<json>' | i2code issue create --session-id abc123
```

### CLI → Filesystem Contract

- **Input:** JSON on stdin + optional `--session-id` flag
- **Output:** Absolute file path on stdout (exit 0) or error message on stderr (exit 1)
- **Side effect:** Creates one `.md` file in `.hitl/issues/active/`

### Hook → CLI Contract

- Hook appends `--session-id <value>` to the Bash command string
- Hook only modifies commands containing `i2code issue create`
- Hook passes through all other Bash commands unmodified

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Latency | Issue creation completes in < 1 second (file write only) |
| Idempotency | Each invocation creates a new file with a unique timestamp-based name |
| Error handling | CLI exits 1 with descriptive stderr on: missing `.hitl/issues/active/`, invalid JSON, missing required fields |
| Testability | CLI logic is unit-testable without Claude Code; hook logic is unit-testable with mock hook payloads |

## Scenarios and Workflows

### Primary Scenario: User Files an Issue Report

1. User types `/claude-issue-report The commit message didn't follow conventions`
2. Claude Code loads the `claude-issue-report` skill
3. Claude performs 5 whys analysis, extracts last 5 messages, suggests improvement
4. Claude runs: `echo '{"description": "The commit message didn't follow conventions", "category": "rule-violation", "analysis": "...", "context": "...", "suggestion": "..."}' | i2code issue create`
5. PreToolUse hook fires, appends `--session-id <id>` to the command
6. CLI parses JSON, generates the markdown file in `.hitl/issues/active/2026-03-18-14-30-00.md`
7. CLI prints the absolute path to stdout
8. Claude reports: "Report captured: /Users/name/project/.hitl/issues/active/2026-03-18-14-30-00.md"

### Scenario: Claude Auto-Suggests an Issue

1. During normal work, Claude realizes it made a mistake (e.g., violated a CLAUDE.md rule)
2. Claude says: "I made a mistake here — I violated the rule about X. Would you like me to file an issue report?"
3. User confirms
4. Flow continues from step 3 of the primary scenario

### Scenario: Missing Tracking Directory

1. User invokes `/claude-issue-report` in a project where `i2code tracking setup` hasn't been run
2. Claude prepares the JSON and pipes it to `i2code issue create`
3. CLI detects `.hitl/issues/active/` doesn't exist
4. CLI prints error to stderr: "Error: .hitl/issues/active/ not found. Run 'i2code tracking setup' first."
5. CLI exits with code 1
6. Claude relays the error to the user

### Scenario: Invalid Category

1. Skill pipes JSON with an unrecognized `category` value
2. CLI rejects the input, prints error to stderr: "Error: invalid category 'foo'. Must be one of: rule-violation, improvement, confusion"
3. CLI exits with code 1

## Constraints and Assumptions

- The `.hitl/issues/active/` directory must already exist (created by `i2code tracking setup`). The CLI does not create it.
- The file format is identical to the current slash command output. Existing `improve review-issues` works without changes.
- The `i2code` CLI is available on PATH (installed via `uv` as defined in `pyproject.toml`).
- The PreToolUse hook matches on command string content (`i2code issue create`). If the user invokes the CLI directly outside Claude Code, no session ID is injected (it defaults to `unknown`).

## Files to Create

| File | Purpose |
|------|---------|
| `src/i2code/issue/__init__.py` | Package init |
| `src/i2code/issue/cli.py` | Click group `issue` with `create` subcommand |
| `src/i2code/issue/create.py` | Issue creation logic (JSON parsing, template rendering, file writing) |
| `claude-code-plugins/idea-to-code/skills/claude-issue-report/SKILL.md` | Skill definition |
| `claude-code-plugins/idea-to-code/hooks/issue-session-injector.js` | PreToolUse hook for session ID injection |

## Files to Delete

| File | Reason |
|------|--------|
| `claude-code-plugins/idea-to-code/commands/claude-issue-report.md` | Replaced by skill |
| `claude-code-plugins/idea-to-code/hooks/issue-session-tagger.js` | Replaced by PreToolUse hook |

## Files to Modify

| File | Change |
|------|--------|
| `src/i2code/cli.py` | Import and register `issue` command group via `main.add_command(issue)` |
| `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json` | Remove `claude-issue-report.md` from `commands`, add `claude-issue-report` to `skills`, replace `issue-session-tagger.js` with `issue-session-injector.js` in hooks, add new PreToolUse entry |

## Testing

### T1: CLI Unit Tests — `i2code issue create`

**Location:** `tests/issue/` (pytest, following existing test directory conventions)

Tests for `src/i2code/issue/create.py` logic, using a `tmp_path` fixture for the target directory:

| Test | What it verifies |
|------|-----------------|
| Happy path | Valid JSON on stdin + `--session-id` → file created with correct content, correct filename, correct frontmatter, absolute path printed to stdout |
| Missing session ID | No `--session-id` flag → file created with `claude_session_id: unknown` |
| Missing required field | JSON missing `description` → exit 1, descriptive stderr |
| Invalid category | `category: "foo"` → exit 1, stderr lists valid categories |
| Invalid JSON | Malformed stdin → exit 1, descriptive stderr |
| Missing target directory | `.hitl/issues/active/` doesn't exist → exit 1, stderr mentions `i2code tracking setup` |
| File format compatibility | Created file is parseable by `improve review-issues` logic (`_find_active_issue_files` finds it, `_is_type_unknown` returns false) |

Use Click's `CliRunner` for invoking the command with stdin input, matching the pattern used in other `i2code` CLI tests.

### T2: Hook Unit Tests — `issue-session-injector.js`

**Location:** `claude-code-plugins/idea-to-code/hooks/issue-session-injector.test.js` (Node.js `assert`, following the `enforce-bash-conventions.test.js` pattern)

| Test | What it verifies |
|------|-----------------|
| Injects session ID | Command containing `i2code issue create` + `session_id` present → command has `--session-id <id>` appended |
| No session ID available | Command containing `i2code issue create` + no `session_id` → command unchanged, exit 0 |
| Non-matching command | Command is `git status` → command unchanged, exit 0 |
| Non-Bash tool | `tool_name` is `Write` → exit 0, no modification |
| Idempotent | Command already contains `--session-id` → not appended twice |

### T3: CLI Smoke Test — `i2code issue --help`

**Location:** Added to `test-scripts/test-subcommands-smoke.sh`

Follows the existing pattern: verify `i2code issue --help` lists `create`, and `i2code issue create --help` exits 0.

### T4: End-to-End Test — Claude Invokes the Skill

**Location:** `tests/issue/` (pytest, alongside the unit tests)

A pytest test that runs `claude -p` as a subprocess to trigger the `/claude-issue-report` skill and verifies the full pipeline: skill → hook → CLI → file.

**Steps:**

1. Create a temporary git repo with `.hitl/issues/active/` directory (using `tmp_path`)
2. Run `claude -p "/claude-issue-report Test issue: the commit message used wrong format"` via `subprocess.run` with `cwd` set to the temp repo
3. Assert:
   - Exit code 0
   - Exactly one `.md` file exists in `.hitl/issues/active/`
   - File has valid YAML frontmatter with `status: active` and a recognized `category`
   - File contains `## 5 Whys Analysis` section
   - File contains `## Context (Last 5 Messages)` section
   - File contains `## Suggested improvement` section
   - File contains `## Resolution` section
   - `claude_session_id` is not `unknown` (hook injected it)

This test validates that the skill, hook, and CLI work together as an integrated system. It requires a Claude API key and network access, so it is marked with a pytest marker (e.g., `@pytest.mark.integration_claude`) to exclude it from the fast test suite.

### Test Runner Integration

| Test script | Runs in |
|-------------|---------|
| `test-scripts/test-subcommands-smoke.sh` (T3) | `test-end-to-end.sh` (fast, no API key needed) |
| `tests/issue/` (T1) | `test-scripts/test-unit.sh` via pytest |
| `claude-code-plugins/idea-to-code/hooks/issue-session-injector.test.js` (T2) | `test-scripts/test-plugin-javascript.sh` via node |
| `tests/issue/` E2E test (T4) | `test-scripts/test-unit.sh` via pytest, but excluded from fast runs by `@pytest.mark.integration_claude` marker |

## Acceptance Criteria

1. **User can invoke `/claude-issue-report`** and get the same file output as before (identical markdown format, same directory, same naming convention)
2. **`i2code issue create`** accepts JSON on stdin and creates a correctly formatted issue file in `.hitl/issues/active/`
3. **Session ID is injected** by the PreToolUse hook — the created file contains the actual `claude_session_id`, not `unknown`
4. **Auto-suggest works** — Claude suggests filing an issue when it detects a mistake, waits for approval, then files it
5. **`improve review-issues`** continues to work without changes (file format compatibility)
6. **Error cases** — CLI exits 1 with descriptive messages for: missing directory, invalid JSON, missing required fields, invalid category
7. **Old artifacts removed** — slash command and PostToolUse hook are deleted; `plugin.json` no longer references them
8. **CLI is independently testable** — `echo '...' | i2code issue create --session-id test` works from the command line without Claude Code
