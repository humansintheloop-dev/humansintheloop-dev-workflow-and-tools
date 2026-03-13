## Brainstorm: Use AskUserQuestion Tool

Update the `i2code brainstorm` prompt template (`brainstorm-idea.md`) to instruct Claude to use the AskUserQuestion tool for asking clarifying questions during brainstorm sessions.

### Problem

Currently, brainstorm questions are asked as plain text. This has two issues:
1. Questions are not consistently formatted as multi-choice, making it harder for users to respond.
2. The AskUserQuestion tool provides a better UX (structured selection UI with labeled options).

### Solution

Modify `src/i2code/prompt-templates/brainstorm-idea.md` to instruct Claude to:
- Prefer formulating questions as multi-choice (2-4 options) whenever possible.
- Use the AskUserQuestion tool for those multi-choice questions.
- Use multi-select when choices aren't mutually exclusive.
- Use preview when comparing concrete artifacts (code, config, mockups).
- Fall back to regular text output only when a question genuinely needs more than 4 options or is fully open-ended.

### Scope

Prompt-only change. No Python code changes needed — the brainstorm already runs as an interactive Claude CLI session with access to AskUserQuestion.

### Classification

User-facing feature (UX improvement to existing command).
