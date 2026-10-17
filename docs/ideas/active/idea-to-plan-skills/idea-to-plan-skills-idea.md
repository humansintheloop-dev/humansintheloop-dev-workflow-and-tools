# Move idea-to-plan prompt guidance into skills

## Problem

The prompts for the idea → spec → plan steps live in `src/i2code/prompt-templates/` and mix three kinds of content: per-run data (file paths), i2code mechanics (output to stdout, validation errors to repair), and reusable guidance (how to brainstorm, how to structure a spec, the plan task format). The guidance is duplicated across templates, and the revise steps are missing parts of it.

- **Idea layout is restated in every prompt.** Each template lists the files it needs, and the layout itself is defined in Python, in the `write-idea` skill and in prose:
  ```
  Use the following files:

  - idea-file: @${IDEA_FILE}
  - discussion-file: @${DISCUSSION_FILE}
  ```
  The `@` syntax also adds file contents to the first message. For a file the step writes, such as the discussion file, that is wrong on the first run and duplicates content on resumed sessions.
- **Idea types A–D are defined three times** and each step works the type out again from the discussion or spec.
- **The plan format is defined in four places**, which already disagree: `create-implementation-plan.md` allows `OUTCOME | INFRA | REFACTOR`, `plan-file-management` documents `INFRA|OUTCOME`.
- **Revise steps are missing the rules.** `revise-plan.md` does not include the task format, so a revision can break it. `revise-spec` builds its prompt inline and does not include the spec quality or Change History rules that `create-spec.md` says apply to later modifications.
- **No test covers Claude's behaviour.** Unit tests check which template is rendered and which paths appear in the prompt. Nothing checks that the spec or plan Claude produces follows the guidance, so moving the guidance cannot be verified.

## Goal

The reusable guidance lives in skills that both the create and revise steps use: an `idea-organization` skill (directory layout, file names, metadata, idea types), `brainstorm-idea`, `write-spec`, `create-plan` (the steel-thread planning method) and `plan-format`. Each prompt template is reduced to the idea directory, the skills to use, and i2code-specific mechanics.

Plugin evals (`claude plugin eval`) for `write-spec` and `plan-format` verify the behaviour, run first against the current templates to set a baseline and then against the skill-based prompts.

## Locations

**Templates to reduce**
- `src/i2code/prompt-templates/brainstorm-idea.md:11` — file list, idea types at `:18`, question-and-answer process
- `src/i2code/prompt-templates/create-spec.md:3` — file list, idea types at `:12`, spec naming at `:64`, quality rules at `:70`, Change History at `:79`
- `src/i2code/prompt-templates/create-implementation-plan.md:4` — file references, idea types at `:32`, plan format from `## Task model` to `## Task granularity guidelines`, "Instructions for Coding Agent" block at `:420`
- `src/i2code/prompt-templates/revise-plan.md:3` — file list; no plan format rules
- `src/i2code/prompt-templates/repair-plan.md` — restates the task format
- `src/i2code/spec_cmd/revise_spec.py:34` — inline prompt with no spec rules

**Call sites**
- `src/i2code/idea_cmd/brainstorm.py:83`
- `src/i2code/spec_cmd/create_spec.py:36`
- `src/i2code/go_cmd/create_plan.py:36` (repair) and `:64` (create)
- `src/i2code/go_cmd/revise_plan.py:30`

**Other definitions of the layout and plan format**
- `src/i2code/implement/idea_project.py:31` — file names; `file_patterns` at `:96`
- `claude-code-plugins/idea-to-code/skills/write-idea/SKILL.md:9` — idea directory and metadata
- `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md:138` — `--task-type <INFRA|OUTCOME>`
- `src/i2code/go_cmd/plan_validator.py:40` — the format the Python side enforces

**Tests that check prompt wiring**
- `tests/idea-cmd/test_brainstorm.py:162`, `tests/spec-cmd/test_create_spec.py:50`, `tests/spec-cmd/test_revise_spec.py:66`, `tests/go-cmd/test_create_plan.py:145`, `tests/go-cmd/test_revise_plan.py:77`

**Unchanged**
- `src/i2code/implement/templates/*.j2` — mostly per-run data and output formats parsed by Python
- `src/i2code/prompt-templates/` files for the `design` and `improve` commands

## Decisions

Classification: **C. Platform/infrastructure capability** (see the discussion file).

- **Skills are self-contained.** `idea-organization`, `brainstorm-idea`, `write-spec`, `create-plan` and `plan-format` each work in an ordinary Claude Code session given an idea directory. The i2code templates add only i2code mechanics.
- **Idea types live in `idea-organization`**, with how an idea records its type. `write-spec` holds the per-type spec sections. `write-idea` refers to `idea-organization` for layout and metadata.
- **The idea type is recorded in the discussion file** in a fixed `## Classification` section with a `**Type:** <letter>. <name>` line. create-spec and create-plan read that line. Metadata keeps only `state`.
- **Prompts stop using `@`** and pass the idea directory as an absolute path, which also fixes relative paths for the standalone commands run without `repo_root`.
- **`plan-format` owns the Instructions for Coding Agent block**, copied verbatim into every plan, content unchanged.
- **TaskType is OUTCOME, INFRA or REFACTOR.** `plan-file-management` and `src/i2code/plan/task_cli.py:19` are corrected, and `plan_validator.py` rejects other values.
- **A unit test keeps `idea-organization` in step with `IdeaProject`** by comparing the skill's file table with the suffixes of `IdeaProject`'s path properties.
- **`revise_spec.py`'s inline prompt becomes a `revise-spec.md` template.**

## Verification

Plugin evals in `claude-code-plugins/idea-to-code/evals/`, run manually by a script under `test-scripts/` with `--no-publish` and a cost ceiling:

1. create-spec produces a type-C spec with the right sections and no open "X or Y" choices.
2. revise-spec adds a `## Change History` entry.
3. create-plan passes the validator rules and contains the Instructions for Coding Agent block.
4. revise-plan keeps the task format.

The script renders each case's prompt with i2code's template code. The current prompts are saved as frozen baseline files and their results committed before the templates change. The skill-based prompts must pass every case 3 of 3 runs. brainstorm-idea has no eval in the first suite.
