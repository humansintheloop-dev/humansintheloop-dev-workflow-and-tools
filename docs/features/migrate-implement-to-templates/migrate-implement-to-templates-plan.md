# Implementation Plan: Migrate Implement Prompts to Jinja2 Templates

## Idea Type

**B. Refactoring/improvement** - Migrate the 5 remaining f-string prompts in implement.py to Jinja2 templates under `src/i2code/implement/templates/`, using the shared `render_template()` helper from `i2code.templates.template_renderer`.

---

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |

### Migration Pattern

Each prompt migration follows these steps:

1. Create the `.j2` template file in `src/i2code/implement/templates/`
2. Replace the f-string in the function with `render_template(template_name, package=__package__, ...)`
3. Run existing tests to verify output is identical
4. Commit

### Key Files

| File | Role |
|------|------|
| `src/i2code/implement/implement.py` | Contains the f-string prompts to migrate |
| `src/i2code/implement/templates/` | Destination for `.j2` template files |
| `src/i2code/templates/template_renderer.py` | Shared `render_template()` helper |
| `tests/implement/test_claude_invocation.py` | Tests for `build_claude_command` (already migrated) |
| `tests/implement/test_github_pr.py` | Tests for triage and fix commands |
| `tests/implement/test_project_setup.py` | Tests for scaffolding prompt |

### Verification

- Test runner: `uv run --with pytest pytest tests/implement/ -m unit`
- Hard rule: NEVER git commit unless you have successfully run the test command and it exits 0

---

## Overview

The `task_execution.j2` template extraction established the pattern. Five f-string prompts remain in `implement.py`:

| Function | Line | Template Name | Purpose |
|----------|------|---------------|---------|
| `build_triage_command` | 729 | `triage_feedback.j2` | Triage PR feedback into categories |
| `build_fix_command` | 790 | `fix_feedback.j2` | Fix PR feedback issues |
| `build_scaffolding_prompt` | 1829 | `scaffolding.j2` | Set up project scaffolding |
| `build_feedback_command` | 2105 | `address_feedback.j2` | Address PR feedback |
| `build_ci_fix_command` | 2150 | `ci_fix.j2` | Fix CI build failures |

---

## Steel Thread 1: PR Feedback Prompts
Migrate the triage and fix feedback prompts, which are closely related.

- [x] **Task 1.1: Migrate build_triage_command prompt to triage_feedback.j2**
  - TaskType: code
  - Entrypoint: `build_triage_command` in implement.py:729
  - Observable: Function uses `render_template("triage_feedback.j2", ...)` instead of f-string. Existing tests pass unchanged.
  - Evidence: `uv run --with pytest pytest tests/implement/ -m unit`
  - Steps:
    1. [x] Create `src/i2code/implement/templates/triage_feedback.j2` with the prompt text
    2. [x] Replace f-string in `build_triage_command` with `render_template` call
    3. [x] Run tests to verify

- [x] **Task 1.2: Migrate build_fix_command prompt to fix_feedback.j2**
  - TaskType: code
  - Entrypoint: `build_fix_command` in implement.py:790
  - Observable: Function uses `render_template("fix_feedback.j2", ...)` instead of f-string. Existing tests pass unchanged.
  - Evidence: `uv run --with pytest pytest tests/implement/ -m unit`
  - Steps:
    1. [ ] Create `src/i2code/implement/templates/fix_feedback.j2` with the prompt text
    2. [ ] Replace f-string in `build_fix_command` with `render_template` call
    3. [ ] Run tests to verify

- [ ] **Task 1.3: Migrate build_feedback_command prompt to address_feedback.j2**
  - TaskType: code
  - Entrypoint: `build_feedback_command` in implement.py:2105
  - Observable: Function uses `render_template("address_feedback.j2", ...)` instead of f-string. Existing tests pass unchanged.
  - Evidence: `uv run --with pytest pytest tests/implement/ -m unit`
  - Steps:
    1. [ ] Create `src/i2code/implement/templates/address_feedback.j2` with the prompt text
    2. [ ] Replace f-string in `build_feedback_command` with `render_template` call
    3. [ ] Run tests to verify

---

## Steel Thread 2: Scaffolding and CI Prompts
Migrate the remaining two prompts.

- [ ] **Task 2.1: Migrate build_scaffolding_prompt to scaffolding.j2**
  - TaskType: code
  - Entrypoint: `build_scaffolding_prompt` in implement.py:1829
  - Observable: Function uses `render_template("scaffolding.j2", ...)` instead of f-string. Existing tests pass unchanged.
  - Evidence: `uv run --with pytest pytest tests/implement/ -m unit`
  - Steps:
    1. [ ] Create `src/i2code/implement/templates/scaffolding.j2` with the prompt text
    2. [ ] Replace f-string in `build_scaffolding_prompt` with `render_template` call
    3. [ ] Run tests to verify

- [ ] **Task 2.2: Migrate build_ci_fix_command prompt to ci_fix.j2**
  - TaskType: code
  - Entrypoint: `build_ci_fix_command` in implement.py:2150
  - Observable: Function uses `render_template("ci_fix.j2", ...)` instead of f-string. Existing tests pass unchanged.
  - Evidence: `uv run --with pytest pytest tests/implement/ -m unit`
  - Steps:
    1. [ ] Create `src/i2code/implement/templates/ci_fix.j2` with the prompt text
    2. [ ] Replace f-string in `build_ci_fix_command` with `render_template` call
    3. [ ] Run tests to verify

---

## Summary

This plan migrates 5 remaining f-string prompts across 2 threads: 3 PR feedback prompts and 2 scaffolding/CI prompts. Each migration follows the pattern established in the `task_execution.j2` extraction. After completion, all Claude prompts in implement.py will be Jinja2 templates, editable without touching Python code.
