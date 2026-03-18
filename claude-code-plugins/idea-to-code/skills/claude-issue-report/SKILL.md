---
name: claude-issue-report
description: Capture mistake or improvement opportunity with 5 whys analysis
user-invokable: true
---

# Claude Issue Report

Capture a mistake or improvement opportunity as a structured issue report with root cause analysis.

## Auto-Suggest Guidance

When you detect that you made a mistake during normal work (e.g., violated a CLAUDE.md rule, used the wrong tool, produced incorrect output), proactively suggest filing an issue:

> "I made a mistake here — [brief description]. Would you like me to file an issue report?"

**Never auto-file.** Always wait for explicit user approval before invoking this skill.

## Steps

1. **Extract the description** from the user's `/claude-issue-report` invocation
2. **Identify your current persona/role** — what system prompt or context you're operating under
3. **Perform 5 whys root cause analysis** of why this mistake or issue happened:
   - Why 1: Why did this happen?
   - Why 2: Why did that happen?
   - Why 3: Why did that happen?
   - Why 4: Why did that happen?
   - Why 5: Root cause
4. **Extract last 5 message exchanges** from the current conversation as context
5. **Suggest an actionable improvement** to prevent recurrence. IMPORTANT: The improvement must be something the **user** can do, such as:
   - Add a rule to CLAUDE.md
   - Configure a tool or linter
   - Create a pre-commit hook
   - Update documentation

   Do NOT write instructions for yourself (Claude) on how to code better.
6. **Determine the category** — one of: `rule-violation`, `improvement`, `confusion`
7. **Pipe all fields as JSON to the CLI** using the Bash tool:

   ```bash
   echo '{"description": "...", "category": "rule-violation", "analysis": "## 5 Whys Analysis\n\n1. **Why did this happen?** ...\n2. **Why did that happen?** ...\n3. **Why did that happen?** ...\n4. **Why did that happen?** ...\n5. **Root cause:** ...", "context": "## Context (Last 5 Messages)\n\n...", "suggestion": "..."}' | i2code issue create
   ```

   All fields are required strings:
   - `description` — the user's description of the issue
   - `category` — one of: `rule-violation`, `improvement`, `confusion`
   - `analysis` — the 5 whys analysis, formatted with the `## 5 Whys Analysis` markdown header
   - `context` — the last 5 message exchanges, formatted with the `## Context (Last 5 Messages)` markdown header
   - `suggestion` — the actionable improvement suggestion (plain text, no header — the CLI adds the header)

   Do NOT pass `--session-id` — the PreToolUse hook injects it automatically.

8. **Report the created file path** back to the user: "Report captured: [path]"

## After Filing the Report

1. Assess current state — if the work is functional, don't undo it
2. Only "fix" if explicitly asked or if the current state is broken
3. Ask for clarification if unsure whether to continue, undo, or just document
