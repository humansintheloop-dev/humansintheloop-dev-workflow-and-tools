---
description: Capture mistake or improvement opportunity with 5 whys analysis
---

Capture a mistake or improvement opportunity. Follow these steps:

1. Extract the description from the user's `/claude-issue-report` command
2. Identify your current persona/role (what system prompt you're operating under)
3. Perform 5 whys root cause analysis of why this mistake happened
4. Extract last 5 message exchanges from the current conversation
5. Create a report in `./.claude/issues/active/` with format:

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

## Resolution

[Empty - filled when resolved]
```

6. Confirm to user: "Report captured: .claude/issues/active/[id].md"