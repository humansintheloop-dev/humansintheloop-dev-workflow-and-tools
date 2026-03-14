# Specification: Use AskUserQuestion Tool in Brainstorm

## Purpose and Background

The `i2code brainstorm` command launches an interactive Claude CLI session that helps users refine software ideas through a structured Q&A process. The session is driven by the prompt template `src/i2code/prompt-templates/brainstorm-idea.md`, which instructs Claude to ask one question at a time, classify the idea, and record the discussion.

Currently, the prompt tells Claude to format multi-choice options as text (A, B, C, D), but Claude doesn't consistently do this. Even when it does, the user must type their answer as free text. The Claude CLI provides a built-in `AskUserQuestion` tool that renders structured selection UI with labeled, described options — a significantly better experience for both asking and answering.

## Target Users

Developers using `i2code brainstorm` to refine software ideas before specification and implementation.

## Problem Statement

1. Claude inconsistently formats questions as multi-choice, even when the prompt requests it. Users must read and type responses to free-form questions.
2. The `AskUserQuestion` tool provides a structured selection UI (clickable options with labels and descriptions) that is faster and easier to use than typing answers to text-based questions.

## Goals

- Every brainstorm question that can be expressed as 2-4 discrete choices uses the `AskUserQuestion` tool.
- Users can respond to most questions with a single click instead of typing.
- Open-ended questions that don't fit the 2-4 option constraint still work via regular text output.

## In-Scope

- Updating the prompt template `src/i2code/prompt-templates/brainstorm-idea.md` to instruct Claude to use `AskUserQuestion`.

## Out-of-Scope

- Changes to Python code (`brainstorm.py`, `claude_runner.py`, `cli.py`).
- Changes to other prompt templates.
- Changes to the prompt used for manual brainstorm sessions (i.e., when a user pastes the brainstorm prompt directly into a Claude session outside `i2code`).

## Functional Requirements

### FR1: Instruct Claude to prefer multi-choice questions

The prompt must instruct Claude to formulate questions as multi-choice (2-4 options) whenever the question has discrete, enumerable answers. This replaces the current instruction "list them as A, B, C, D".

### FR2: Instruct Claude to use AskUserQuestion for multi-choice questions

When a question has 2-4 discrete options, Claude must use the `AskUserQuestion` tool instead of printing the question as text. Each option must have:
- A concise `label` (1-5 words)
- A `description` explaining what the option means or its implications

### FR3: Instruct Claude to use appropriate AskUserQuestion features

The prompt must instruct Claude to:
- Use `multiSelect: true` when choices are not mutually exclusive (e.g., "Which concerns apply?")
- Use the `preview` field when comparing concrete artifacts (code snippets, config examples, mockups)
- Use a short, descriptive `header` tag (max 12 chars) for each question

### FR4: Instruct Claude to fall back to text for unsuitable questions

When a question is genuinely open-ended or has more than 4 possible answers, Claude must use regular text output instead of `AskUserQuestion`. The "Other" option (automatically provided by the tool) handles cases where none of the offered choices fit.

### FR5: Remove conflicting instructions

The current prompt contains the instruction:
```
If there are multiple options for a question, list them as A, B, C, D, and I will choose one.
```
This must be replaced with the AskUserQuestion instructions to avoid conflicting guidance.

## Security Requirements

Not applicable. This is a prompt template change with no authentication, authorization, or data access implications. The brainstorm runs locally as a CLI process under the user's own credentials.

## Non-Functional Requirements

### UX
- The brainstorm flow must feel conversational — tool-based questions should not break the natural rhythm of the discussion.
- The user must always be able to provide a free-text answer via the "Other" option (this is built into AskUserQuestion).

### Reliability
- If AskUserQuestion is unavailable (e.g., running in a non-interactive context), the brainstorm should still function. The prompt should not make AskUserQuestion the only possible way to ask questions.

## Success Metrics

- Multi-choice questions in brainstorm sessions use the `AskUserQuestion` tool (observable by the structured selection UI appearing).
- Users can complete a brainstorm session answering most questions via selection rather than typing.

## Epics and User Stories

### Epic: AskUserQuestion Integration

**US1:** As a developer brainstorming an idea, I want clarifying questions presented as clickable multi-choice options so I can respond quickly without typing.

**US2:** As a developer brainstorming an idea, I want open-ended questions to still appear as regular text so the brainstorm flow isn't artificially constrained to 4 choices.

**US3:** As a developer brainstorming an idea, I want to see descriptions for each option so I understand the implications of my choice before selecting.

## Scenarios

### Primary End-to-End Scenario: Brainstorm with AskUserQuestion

1. User runs `i2code idea brainstorm <directory>`.
2. If no idea file exists, editor opens for the user to describe their idea.
3. Claude reads the idea file and begins the brainstorm Q&A.
4. Claude asks the first clarifying question using `AskUserQuestion` with 2-4 labeled options.
5. User selects an option (or chooses "Other" to type a custom answer).
6. Claude records the answer in the discussion file and asks the next question, again using `AskUserQuestion` where appropriate.
7. For a question that is genuinely open-ended, Claude asks via regular text output.
8. After sufficient questions, Claude asks the final "ready to proceed?" question using `AskUserQuestion`.
9. Claude records the classification and all Q&A in the discussion file.

### Scenario: Question exceeds option limit

1. Claude needs to ask a question with more than 4 possible answers.
2. Claude falls back to regular text output, listing the options as text.
3. User types their answer.
4. Brainstorm continues normally.

### Scenario: User selects "Other"

1. Claude presents a multi-choice question via `AskUserQuestion`.
2. None of the options fit the user's intent.
3. User selects "Other" and types a custom response.
4. Claude incorporates the custom response and continues.
