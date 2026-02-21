---
name: ask-a-friend
description: When stuck on a problem, formulate a well-structured question and copy it to the clipboard for pasting into ChatGPT. Claude should use this skill when debugging efforts stall or when an outside perspective would help.
---

# Ask a Friend

When you're stuck and need an outside perspective, use this skill to formulate a clear question for ChatGPT.

## When to Use

- Debugging has stalled after multiple failed hypotheses
- The user says they want to ask someone else
- A problem involves platform/tool behavior outside your direct knowledge

## Steps

1. **Ask permission first** — unless the user explicitly invoked this skill, tell the user you're stuck and suggest asking a friend before proceeding. Wait for approval.
2. **Summarize the problem** — what you're trying to do and the specific symptom
3. **List what you've verified** — tests run, hypotheses confirmed/eliminated
4. **List what you've tried** — failed fixes and why they didn't work
5. **State the specific question** — what you need answered
6. **Copy to clipboard** — use `pbcopy` (macOS) to put the formatted question on the clipboard
7. **Tell the user** — confirm it's on their clipboard and ready to paste

## Question Format

Use this structure (adapted to the specific problem):

```
## Problem: [one-line summary]

### Setup
[Relevant code, configuration, or architecture — keep it minimal but complete]

### Symptom
[What happens vs. what should happen]

### What I've verified
[Bulleted list of tests/checks that passed or confirmed behavior]

### What I've tried (didn't help)
[Numbered list of attempted fixes and why each failed]

### Key facts
[Bullet points of relevant constraints, versions, platform details]

### Question
[The specific question you need answered]
```

## Guidelines

- **Be concise** — include enough context to reproduce, not the full investigation history
- **Include code** — show the actual code, not just descriptions of it
- **State versions** — language/runtime version, OS, relevant tool versions
- **Show the matrix** — if some scenarios work and others don't, show that clearly (this is often the most useful signal)
- **End with a specific question** — not "what's wrong?" but a focused question that narrows the problem space
- **Language-agnostic** — this skill applies to any technology (Python, Java, shell, Docker, CI, infrastructure, etc.)
