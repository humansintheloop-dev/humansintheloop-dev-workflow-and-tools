Here's the implementation plan:

---

# Implementation Plan: Use AskUserQuestion Tool in Brainstorm

## Idea Type

**A. User-facing feature** — UX improvement to the existing `i2code brainstorm` command.

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

## Context

This is a **prompt-template-only change**. The file to modify is `src/i2code/prompt-templates/brainstorm-idea.md`. No Python code changes are needed — the brainstorm already runs as an interactive Claude CLI session with access to the `AskUserQuestion` tool.

The `AskUserQuestion` tool supports:
- 2-4 options, each with a `label` (1-5 words) and `description`
- `multiSelect: true` for non-mutually-exclusive choices
- `preview` field for comparing concrete artifacts (code, config, mockups)
- A `header` tag (max 12 chars) for categorizing the question
- An automatic "Other" option that allows free-text input

## Steel Thread 1: Update Brainstorm Prompt to Use AskUserQuestion

This is the only steel thread needed. The change is a single prompt template file edit with no code dependencies.

- [ ] **Task 1.1: Replace text-based multi-choice instructions with AskUserQuestion instructions**
  - TaskType: OUTCOME
  - Entrypoint: Read `src/i2code/prompt-templates/brainstorm-idea.md`
  - Observable: The prompt template (1) no longer contains the instruction "list them as A, B, C, D", (2) contains instructions to use `AskUserQuestion` for multi-choice questions with labeled/described options, (3) contains instructions to fall back to regular text for open-ended questions or questions with more than 4 options
  - Evidence: `grep -c "AskUserQuestion" src/i2code/prompt-templates/brainstorm-idea.md` returns a non-zero count AND `grep -c "list them as A, B, C, D" src/i2code/prompt-templates/brainstorm-idea.md` returns 0 AND existing CI passes
  - Steps:
    - [ ] Read `src/i2code/prompt-templates/brainstorm-idea.md` to understand the current prompt structure and locate the conflicting "list them as A, B, C, D" instruction (FR5)
    - [ ] Remove the "list them as A, B, C, D" instruction (FR5)
    - [ ] Add instruction: prefer formulating questions as multi-choice (2-4 options) whenever the question has discrete, enumerable answers (FR1)
    - [ ] Add instruction: use `AskUserQuestion` tool for multi-choice questions; each option must have a concise `label` (1-5 words) and a `description` explaining the option's meaning or implications (FR2)
    - [ ] Add instruction: use a short, descriptive `header` tag (max 12 chars) for each question (FR3)
    - [ ] Add instruction: use `multiSelect: true` when choices are not mutually exclusive (e.g., "Which concerns apply?") (FR3)
    - [ ] Add instruction: use the `preview` field when comparing concrete artifacts like code snippets, config examples, or mockups (FR3)
    - [ ] Add instruction: fall back to regular text output when a question is genuinely open-ended or has more than 4 possible answers (FR4)
    - [ ] Add instruction: if `AskUserQuestion` is unavailable, fall back to text-based questions (reliability NFR)
    - [ ] Verify the prompt reads naturally and the new instructions integrate with the existing prompt flow (UX NFR — tool-based questions should not break the conversational rhythm)
    - [ ] Run existing project tests to confirm nothing is broken
