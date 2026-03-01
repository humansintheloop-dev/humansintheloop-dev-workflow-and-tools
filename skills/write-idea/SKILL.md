---
name: write-idea
description: Summarize the current discussion into an idea file. Use when the user asks to capture an idea, write an idea file, or after a discussion identifies a refactoring or feature worth pursuing.
user-invokable: true
---

# Write Idea File

Summarize the current discussion into an idea file at `docs/ideas/draft/<name>/<name>-idea.md`.

## Steps

1. **Ask for the name** — use AskUserQuestion to ask:
   "What name should I use for the idea directory? (e.g., `claude-runner-run`)"
   Suggest a kebab-case name based on the discussion topic.

2. **Write the idea file** — `docs/ideas/draft/<name>/<name>-idea.md` with these sections:

### Problem
What's wrong, duplicated, or missing. Include a short code example if the discussion involved one.

### Goal
The desired end state in 1-2 sentences. This is *what* should change, not *how* to implement it.

### Locations
Group by role. Use `file:line` references. Typical groupings:

- **Definition** — where the class/function/module is defined
- **Construction sites** — where instances are created
- **Call sites** — where the behavior is invoked or the pattern is duplicated
- **Unchanged** — locations explicitly out of scope

Omit groupings that don't apply.

## Guidelines

- **Concise** — an idea file is a goal description, not an implementation plan
- **Concrete** — include file:line references, not vague descriptions
- **No implementation details** — don't specify the step-by-step approach; that belongs in a plan file
- **Derive from discussion** — extract the problem, goal, and locations from what was discussed in this conversation
