---
name: brainstorm-idea
description: Use when refining an idea in an idea directory through questions and answers and classifying it.
---

# Brainstorm Idea

Brainstorming refines an idea through questions and answers, and classifies it.
It captures enough detail to later write the right kind of specification and a steel-thread implementation plan.

Locate the idea's files following the `idea-to-code:idea-organization` skill.

## Outputs

- The refined idea, written to the idea file (`<name>-idea.md`).
- Every question and answer, written to the discussion file (`<name>-discussion.md`).
- The idea's type and the rationale for it, written to the discussion file as the `## Classification` section described in `idea-organization`.
  The type is one of the four idea types defined in `idea-organization`.

## Constraints

- Do not write a specification.
- Do not write an implementation or steel-thread plan.
- Your role is to ask questions, refine the idea and record the discussion.

## Process

- If the discussion file already exists, read it first to understand what has already been covered.
- **Analyze the codebase first** - Before asking questions about current system state, explore the code to understand existing architecture, entities, and relationships. Reserve questions for:
  - User preferences and decisions
  - Requirements clarification
  - Business context not observable in code
  - Priorities and constraints
- **Derive obvious conclusions** - Before asking a question, verify it cannot be derived from prior answers. If the answer follows logically from established decisions, state the conclusion and move on. Reserve questions for genuinely ambiguous or preference-based decisions.
- Ask one question at a time so that you develop a thorough, step-by-step understanding of the idea.
- **After each answer, immediately append the Q&A to the discussion file before asking the next question.** Do not batch discussion file updates — the file should always reflect the full conversation so far.
- Each question should build on the previous answers.
- Define sensible and easily changeable default assumptions so that the discussion can focus on the most important aspects.
- When a question has discrete, enumerable answers, prefer formulating it as multi-choice with 2-4 options.
- For multi-choice questions, use the `AskUserQuestion` tool instead of printing options as text. For each option, provide a concise `label` (1-5 words) and a `description` explaining what the option means or its implications. Include a short, descriptive `header` tag (max 12 chars) for each question.
- Use `multiSelect: true` when choices are not mutually exclusive (e.g., "Which concerns apply?").
- Use the `preview` field when comparing concrete artifacts like code snippets, config examples, or mockups.
- Fall back to regular text output when a question is genuinely open-ended or has more than 4 possible answers.
- If `AskUserQuestion` is unavailable, fall back to text-based questions with options listed as A, B, C, D.
- **Proactively identify downstream impacts** - When analyzing architectural changes:
  1. Trace event flows - which services consume events from affected components?
  2. Identify cross-cutting concerns - authorization, auditing, monitoring, caching
  3. Check for CQRS replicas - what other services maintain replicas of affected data?
  4. Review integration points - APIs, messaging, shared data
- Write the refined idea to the idea file and the `## Classification` section to the discussion file.

Remember: only one question at a time.

## Finishing

- Continue until you believe you have enough information to later create a developer-ready specification and a steel-thread-ready plan (in subsequent steps, not in this one).
- When you believe all relevant details have been gathered, do NOT generate the specification.
  Instead, ask:
  "Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?"
- After asking this question and recording the answer in the discussion file, STOP. Do not generate the specification or a plan.
