---
description: Capture mistake or improvement opportunity with 5 whys analysis
---

Capture a mistake or improvement opportunity. Follow these steps:

1. Extract the description from the user's `/claude-issue-report` command
2. Identify your current persona/role (what system prompt you're operating under)
3. Perform 5 whys root cause analysis of why this mistake happened
4. Extract last 5 message exchanges from the current conversation
5. Suggest an actionable improvement to prevent recurrence. IMPORTANT: The improvement must be something the USER can do, such as:
   - Add a rule to CLAUDE.md
   - Configure a tool or linter
   - Create a pre-commit hook
   - Update documentation
   Do NOT write instructions for yourself (Claude) on how to code better
6. Create a report in the project root's `.claude/issues/active/` directory using an absolute path (first check that directory exists, create if not). IMPORTANT: Use the project root directory (where you started), not the current working directory if you have changed directories during the session. The file path must be absolute (e.g., `/Users/name/project/.claude/issues/active/YYYY-MM-DD-HH-MM-SS.md`). Format:

```markdown
---
id: YYYY-MM-DD-HH-MM-SS
created: ISO8601 timestamp
status: active
category: rule-violation|improvement|confusion
claude_session_id: unknown
---

# [User's description]

## 5 Whys Analysis

1. **Why did this happen?** [Your analysis]
2. **Why did that happen?** [Your analysis]
3. **Why did that happen?** [Your analysis]
4. **Why did that happen?** [Your analysis]
5. **Root cause:** [Your conclusion]

## Context (Last 5 Messages)

[Extracted conversation]

## Suggested improvement

[Suggested improvement to prevent recurrence]

## Resolution

[Empty - filled when resolved]
```

6. Confirm to user: "Report captured: [absolute-path-to-file]"