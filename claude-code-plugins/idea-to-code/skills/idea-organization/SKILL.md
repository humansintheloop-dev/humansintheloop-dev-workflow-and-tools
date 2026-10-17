---
name: idea-organization
description: Use when reading, creating or locating files in an idea directory under docs/ideas/, or when determining or recording an idea's type.
---

# Idea Organization

## Directory layout

An idea named `<name>` lives in `docs/ideas/active/<name>/` or `docs/ideas/archived/<name>/`.
A new idea is created in `docs/ideas/active/<name>/`.
Every file in the directory is named `<name>-<suffix>`.

## Lifecycle metadata

`<name>-metadata.yaml` contains one key, `state`, with one of these values:

- `draft`
- `ready`
- `wip`
- `completed`
- `abandoned`

A new idea starts with `state: draft`.
Archival is independent of state: an idea in `docs/ideas/archived/` can have any state.

## Idea files

| File | Purpose | Written by |
|------|---------|------------|
| `<name>-idea.md` | the idea (`.txt` also accepted) | user, brainstorm |
| `<name>-discussion.md` | brainstorm questions, answers and classification | brainstorm |
| `<name>-spec.md` | specification | create-spec, revise-spec |
| `<name>-plan.md` | steel-thread implementation plan | i2code (create-plan output), revise-plan, plan-file-management |
| `<name>-design.md` | design document | design command |
| `<name>-stories.md` | user stories | not written by a current step |
| `<name>-story-plan.md` | plan with stories | not written by a current step |
| `<name>-metadata.yaml` | lifecycle state | i2code, `write-idea` |
| `<name>-sessionID.txt` | Claude session id | i2code only — do not edit |
| `<name>-implement-config.yaml` | implement options | i2code only — do not edit |
| `<name>-broken-plan.md` | plan that failed validation after repair | i2code only — do not edit |
| `<name>-wt-state.json` | worktree workflow state | i2code only — do not edit |

## Idea types

Every idea has exactly one of these four types.

**A. User-facing feature** — new or changed behaviour that end users of an application see and use, such as a screen, an API operation or a workflow.
Its specification is PRD-style: personas, functional requirements, security requirements, and the user scenarios the plan turns into steel threads.

**B. Architecture POC** — a proof of concept that validates a critical architectural concern, such as a technology choice, an integration style or a quality attribute.
Its specification states the architectural question, the hypotheses, the measurements that answer them, and the scenarios that exercise the architecture.

**C. Platform/infrastructure capability** — a capability that other code, tools or teams consume rather than end users, such as a library, a CLI, a build or deployment mechanism, or a developer workflow.
Its specification names the consumers and defines the capabilities, contracts and integration points they rely on.

**D. Educational/example repository** — code whose purpose is to teach a concept or demonstrate a pattern.
Its specification states the learning goals and the audience, and the scenarios that show each concept in a way a reader can follow.

## Classification

Brainstorming ends the discussion file (`<name>-discussion.md`) with this section:

```markdown
## Classification

**Type:** C. Platform/infrastructure capability

**Rationale:** <one or more sentences>
```

The type line has the form `**Type:** <letter>. <name>`, with the name exactly as written in [Idea types](#idea-types).

A step that needs the idea's type reads the `**Type:**` line.
It does not infer the type from the prose of the idea, the discussion or the spec.

When the discussion file has no `**Type:**` line, tell the user that the idea's type is not recorded and ask which of A–D it is before continuing.
