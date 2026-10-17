---
name: write-spec
description: Use when creating or changing the specification (<name>-spec.md) of an idea.
---

# Write Spec

A specification is a developer-ready description of an idea.
It is the input to a later steel-thread implementation plan.
It never contains that plan.

## Inputs

Locate the idea's files following the `idea-to-code:idea-organization` skill.

1. Read the idea file (`<name>-idea.md`) and the discussion file (`<name>-discussion.md`).
2. Read the idea's type from the `**Type:**` line of the discussion file, as described in `idea-organization`.
   Do not infer the type from prose.
   When the discussion file has no `**Type:**` line, tell the user that the idea's type is not recorded and ask which of A–D it is before writing the specification.

## Sections by idea type

Based on the type, produce the corresponding specification:

A. If it is a **user-facing feature**, produce a PRD-style spec that includes:
   - Purpose and background
   - Target users and personas
   - Problem statement and goals
   - In-scope and out-of-scope
   - High-level functional requirements
   - **Security requirements** - For each endpoint/operation, specify:
     - Who can perform this operation (role/persona)
     - What authorization checks are required
     - Any additional constraints (e.g., can only operate on own resources)
   - Non-functional requirements (UX, performance, reliability, etc.)
   - Success metrics
   - Epics and user stories
   - A set of user-facing scenarios appropriate for defining a later steel-thread plan
     (identify the main end-to-end scenario, but do NOT generate a plan)

B. If it is an **architecture POC**, produce an Architecture Validation Requirements document that includes:
   - Architectural concern / risk being addressed
   - Architectural goals (quality attributes such as security, performance, etc.)
   - Required architectural capabilities
   - Validation scenarios (quality attribute scenarios)
   - One primary end-to-end thread the POC must demonstrate
   - Identify any possible refinements to that thread (but do NOT generate steel-thread stages or a plan)
   - Constraints and assumptions
   - Acceptance criteria for declaring the POC successful

C. If it is a **platform/infrastructure capability**, produce a Platform Capability Specification that includes:
   - Purpose and context
   - Consumers (teams, services, or systems that will use the platform capability)
   - Capabilities and behaviors the platform must provide
   - High-level APIs, contracts, or integration points
   - Non-functional requirements and SLAs
   - Scenarios and workflows (including one primary end-to-end scenario)
     These prepare for a later steel-thread plan but do NOT create that plan.
   - Constraints and assumptions
   - Acceptance criteria

D. If it is an **educational/example repo**, produce a Didactic Example Specification that includes:
   - Learning goals
   - Concepts and patterns the example must demonstrate
   - End-to-end example flows
   - Capabilities and constraints
   - Scenarios that a user of the example should be able to run (including a primary scenario)
     These scenarios support a later steel-thread plan but do NOT create that plan.

## Naming

Save the specification as a markdown document in the same directory as the idea file.
For the idea file `<name>-idea.md`, the specification file is `<name>-spec.md`.
Write the file with the Write tool. Do not only show the specification in the conversation, and do not ask for confirmation before writing it.

## Quality rules

- **Be decisive** — A spec must not say "do X or Y". Every decision point needs a single answer. When the idea and discussion leave a point undecided, choose the answer that best fits them and record it as an assumption in the spec. Do not write "optionally", "TBD", "to be decided", open questions or future options.
- **No plan** — The spec contains no implementation plan: no tasks, phases, milestones, steel threads, implementation steps or build order.
- **Be concrete** — Don't use vague placeholders or internal jargon without explanation. Reference actual values, formats, and names from the existing codebase. For example, specify the exact payload format a template produces, not "add a payload description".

## Change History

These rules apply to every change made after the specification is first written, including changes made during an interactive revision.

1. Add or update the `## Change History` section. It is the last section of the document.
2. Add one entry per change, headed `### YYYY-MM-DD: <brief description>`.
3. Under the heading, state what changed and why.
