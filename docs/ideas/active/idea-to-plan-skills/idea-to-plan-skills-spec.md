# Platform Capability Specification: Idea-to-plan guidance as skills

**Idea type:** C. Platform/infrastructure capability

Sources: `idea-to-plan-skills-idea.md`, `idea-to-plan-skills-discussion.md` (Q1–Q13).

---

## 1. Purpose and context

The i2code idea → spec → plan steps send Claude prompts rendered from `src/i2code/prompt-templates/`. Those templates mix three kinds of content:

| Kind | Example | Where it belongs after this work |
|------|---------|----------------------------------|
| Per-run data | idea, discussion, spec and plan paths | the template, as one `${IDEA_DIRECTORY}` variable |
| i2code mechanics | "output the plan to stdout, do not write files"; the repair pass's validation errors | the template |
| Reusable guidance | how to brainstorm, the idea types, spec sections, the plan task format | a skill in the `idea-to-code` plugin |

Today the guidance is duplicated and inconsistent:

- The idea types A–D are defined in `brainstorm-idea.md:18`, `create-spec.md:7` and `create-implementation-plan.md:28`. create-spec infers the type from discussion prose. create-plan infers it again from the spec.
- The plan task format is defined in `create-implementation-plan.md`, `repair-plan.md`, `plan-file-management/SKILL.md:138` and `src/i2code/plan/task_cli.py:19`. The first two allow `OUTCOME | INFRA | REFACTOR`. The last two say `INFRA` or `OUTCOME`. `src/i2code/go_cmd/plan_validator.py` checks only that `TaskType` is present.
- `revise-plan.md` has no task format rules. `revise_spec.py:34` builds an inline prompt with no spec quality or Change History rules.
- Every template except revise-spec references files with `@path`. This inlines the file into the first message, including files the step is about to write (the discussion file), and inlines them again on a resumed session.
- The standalone commands (`i2code idea brainstorm`, `i2code spec create|revise`, `i2code plan create|revise`) pass no `repo_root`. Claude then runs with the idea directory as its working directory. A relative idea path argument such as `docs/ideas/active/x` (returned unchanged by `src/i2code/idea/resolver.py:26`) then points nowhere.
- No test checks what Claude produces from these prompts. The unit tests only check which template is rendered and which paths appear in it.

This capability moves the reusable guidance into five self-contained skills, reduces the templates to data plus mechanics, and adds plugin evals that measure Claude's output before and after the move.

## 2. Consumers

| Consumer | Code | Mode | Skills it names |
|----------|------|------|-----------------|
| brainstorm | `src/i2code/idea_cmd/brainstorm.py:83` | interactive, resumable session | `idea-organization`, `brainstorm-idea` |
| create-spec | `src/i2code/spec_cmd/create_spec.py:36` | interactive, resumes brainstorm session | `idea-organization`, `write-spec` |
| revise-spec | `src/i2code/spec_cmd/revise_spec.py:34` | interactive | `idea-organization`, `write-spec` |
| create-plan | `src/i2code/go_cmd/create_plan.py:64` | batch, plan returned on stdout | `idea-organization`, `create-plan`, `plan-format` (plus the existing `${PLAN_SKILLS}` list) |
| repair-plan | `src/i2code/go_cmd/create_plan.py:36` | batch, plan returned on stdout | `plan-format` |
| revise-plan | `src/i2code/go_cmd/revise_plan.py:30` | interactive | `idea-organization`, `plan-format`, `plan-file-management` |
| ordinary Claude Code session | — | any | any of the five, triggered by their descriptions |
| `write-idea` skill | `claude-code-plugins/idea-to-code/skills/write-idea/SKILL.md` | — | refers to `idea-organization` for layout and metadata |

Each consumer is reached both through `i2code go` (`src/i2code/go_cmd/orchestrator.py:150`–`176`, which passes `repo_root`) and through the standalone commands (`src/i2code/idea_cmd/cli.py:33`, `src/i2code/spec_cmd/cli.py:23` and `:32`, `src/i2code/plan/cli.py:40` and `:49`, which do not).

## 3. Capabilities and behaviours

### 3.1 Skill `idea-to-code:idea-organization`

Location: `claude-code-plugins/idea-to-code/skills/idea-organization/SKILL.md`, added to `skills` in `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`.

Description (trigger): use when reading, creating or locating files in an idea directory under `docs/ideas/`, or when determining or recording an idea's type.

Contents:

1. **Directory layout.** An idea named `<name>` lives in `docs/ideas/active/<name>/` or `docs/ideas/archived/<name>/`. Every file in it is named `<name>-<suffix>`.
2. **Lifecycle metadata.** `<name>-metadata.yaml` contains one key, `state`, with a value from `draft`, `ready`, `wip`, `completed`, `abandoned` (`src/i2code/idea/resolver.py:9`). A new idea starts with `state: draft`. Archival is independent of state.
3. **File table.** A markdown table with the heading `## Idea files` and exactly these columns: `File`, `Purpose`, `Written by`. One row per `IdeaProject` path property (`src/i2code/implement/idea_project.py`):

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

   (The discussion recorded 13 properties; the code has 12. The table follows the code.)
4. **Idea types.** The four types, each with a one-paragraph definition:
   - `A. User-facing feature`
   - `B. Architecture POC`
   - `C. Platform/infrastructure capability`
   - `D. Educational/example repository`
5. **Recording the type.** The discussion file ends with this section, written by brainstorm:
   ```markdown
   ## Classification

   **Type:** C. Platform/infrastructure capability

   **Rationale:** <one or more sentences>
   ```
   The `**Type:**` line is `**Type:** <letter>. <name>` with the name exactly as in item 4. A step that needs the type reads this line. It does not infer the type from prose. If the discussion file has no `**Type:**` line, the step tells the user the type is not recorded and asks for it before continuing.

### 3.2 Skill `idea-to-code:brainstorm-idea`

Location: `claude-code-plugins/idea-to-code/skills/brainstorm-idea/SKILL.md`.

Description (trigger): use when refining an idea in an idea directory through questions and answers and classifying it.

Contents, moved from `src/i2code/prompt-templates/brainstorm-idea.md` with the idea types replaced by a reference to `idea-organization`:

- Read the discussion file first if it exists.
- Analyse the codebase before asking about current system state.
- Derive conclusions that follow from earlier answers instead of asking.
- One question at a time, each building on earlier answers.
- Use `AskUserQuestion` for multi-choice questions (2–4 options, `label`, `description`, `header` ≤ 12 chars, `multiSelect` when not exclusive, `preview` for comparing artifacts). Fall back to text options A–D if the tool is unavailable.
- Append each question and answer to the discussion file before asking the next question.
- State sensible, changeable default assumptions.
- Identify downstream impacts (event flows, cross-cutting concerns, replicas, integration points).
- Write the refined idea to the idea file and the `## Classification` section (3.1 item 5) to the discussion file.
- Do not write a specification or a plan.
- When enough is known, ask "Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?", record the answer, and stop.

### 3.3 Skill `idea-to-code:write-spec`

Location: `claude-code-plugins/idea-to-code/skills/write-spec/SKILL.md`.

Description (trigger): use when creating or changing the specification (`<name>-spec.md`) of an idea.

Contents, moved from `src/i2code/prompt-templates/create-spec.md`:

1. **Inputs.** Read the idea file and discussion file. Read the type from the `**Type:**` line (3.1 item 5).
2. **Per-type sections.** The four section lists (A PRD-style spec including security requirements; B Architecture Validation Requirements; C Platform Capability Specification; D Didactic Example Specification), unchanged from `create-spec.md:14`–`61`. Each list says scenarios prepare for a later steel-thread plan and the spec contains no plan.
3. **Naming.** `<name>-idea.md` → `<name>-spec.md` in the same directory.
4. **Quality rules.** Be decisive (no "X or Y"); be concrete (actual values, formats and names from the codebase).
5. **Change History.** Applies to every change after the spec is first written, including changes made during an interactive revision. Add or update `## Change History` as the last section. One entry per change, headed `### YYYY-MM-DD: <brief description>`, with what changed and why.

### 3.4 Skill `idea-to-code:plan-format`

Location: `claude-code-plugins/idea-to-code/skills/plan-format/SKILL.md`.

Description (trigger): use when writing, revising or repairing an implementation plan file (`<name>-plan.md`).

Contents, moved from `src/i2code/prompt-templates/create-implementation-plan.md` (from `## Task model` through `## Task granularity guidelines`, and the Instructions block at `:420`) and `repair-plan.md`:

1. **Plan skeleton**, in this order:
   ```markdown
   # Implementation Plan: <title>

   ## Idea Type

   **C. Platform/infrastructure capability** — <one-sentence rationale>

   ## Instructions for Coding Agent
   ...(verbatim block, item 6)...

   ## Overview
   ...

   ## Steel Thread 1: <description>
   ...
   ## Change History
   ```
   `# Implementation Plan:`, `## Idea Type` and `## Overview` are the headings `src/i2code/plan_domain/plan.py` reads. The `## Idea Type` letter and name are copied from the discussion file's `**Type:**` line.
2. **Task model and task types.** `OUTCOME`, `INFRA` and `REFACTOR`, with the definitions at `create-implementation-plan.md:221`–`277`. No other value is valid.
3. **Steel thread heading format** (`## Steel Thread N: Description`).
4. **Task structure**, exactly:
   ```markdown
   - [ ] **Task X.Y: Outcome-oriented description**
     - TaskType: OUTCOME
     - Entrypoint: `<command>`
     - Observable: <what is observed>
     - Evidence: `<command>`
     - Steps:
       - [ ] <step>
   ```
5. **Rules:** code reference formatting in steps, evidence requirements, test-first task structure, no ambiguous alternatives ("X or Y" / "X (or Y)" resolved to one action), task granularity.
6. **The Instructions for Coding Agent block**, verbatim from `create-implementation-plan.md:426` to the end of its fenced block, with the instruction that every plan contains it unchanged after `## Idea Type`.
7. **Revisions.** Structural changes (insert, delete, reorder, renumber) use the `plan-file-management` skill. Every change requested in a conversation is recorded under `## Change History`.

### 3.5 Prompt templates

All templates take one directory variable, `${IDEA_DIRECTORY}`, set to `project.directory` (absolute, see 3.7). They no longer contain `@`.

| Template | Contains after the change |
|----------|---------------------------|
| `brainstorm-idea.md` | idea directory; "Use `idea-to-code:idea-organization` and `idea-to-code:brainstorm-idea`" ; the step instruction (refine the idea in this directory) |
| `create-spec.md` | idea directory; the two skills; "write the specification; do not write a plan" |
| `revise-spec.md` (new, replaces the inline prompt in `revise_spec.py:34`) | idea directory; the two skills; "I will ask you to make changes to the specification" |
| `create-implementation-plan.md` | idea directory; "Use `idea-to-code:idea-organization`, `idea-to-code:create-plan` and `idea-to-code:plan-format`"; `## Skills to Follow` with `${PLAN_SKILLS}`; the stdout mechanics (`create-implementation-plan.md:12`–`15`) |
| `repair-plan.md` | "Use `idea-to-code:plan-format`"; the repair constraints (fix only the listed errors, no new threads, preserve numbering, full plan on stdout, no commentary); `$VALIDATION_ERRORS`; `$PLAN_TEXT`. The restated task format is removed. |
| `revise-plan.md` | idea directory; the three skills; "I will ask you to make changes to the plan" |

### 3.6 Skill `idea-to-code:create-plan`

Location: `claude-code-plugins/idea-to-code/skills/create-plan/SKILL.md`.

Description (trigger): use when creating a steel-thread implementation plan for an idea from its idea, discussion and spec files.

Contents, moved from `src/i2code/prompt-templates/create-implementation-plan.md`:

1. **Inputs.** Read the idea, discussion and spec files. Read the type from the discussion's `**Type:**` line (3.1 item 5).
2. `## Implementation context`: paths and commands relative to the project root, no idea directory prefix.
3. `## Analyze existing code BEFORE planning`.
4. `## General principles`, including `### Incremental build-up`, and how scenarios map to steel threads by idea type.
5. `## Task 1.1 Requirements` and its subsections (Java/Gradle, Docker Compose, infrastructure-only, anti-patterns, valid example).
6. `## Goal`.
7. **Format.** The plan follows `plan-format`.

The skill does not say where the plan is written. Run by i2code, the template says to return it on stdout. In an ordinary session, Claude writes `<name>-plan.md` in the idea directory.

`revise-plan` and `repair-plan` do not name `create-plan`. They change an existing plan and need only `plan-format`.

### 3.7 Absolute idea directory

`IdeaProject.__init__` (`src/i2code/implement/idea_project.py:18`) stores `os.path.abspath(directory)`. `name` is still the basename. All derived paths become absolute. `worktree_idea_project` (`:127`) keeps working because `os.path.relpath` accepts absolute paths.

### 3.8 TaskType values

- `plan_validator.py` adds an error `Invalid TaskType '<value>' in Task X.Y (expected OUTCOME, INFRA or REFACTOR)` when the value is not one of the three. The existing repair pass receives it like any other error.
- `src/i2code/plan/task_cli.py:19` help text becomes `Task type (OUTCOME, INFRA or REFACTOR)`.
- `plan-file-management/SKILL.md` replaces every `--task-type <INFRA|OUTCOME>` with `--task-type <OUTCOME|INFRA|REFACTOR>`.

### 3.9 Other skill updates

- `write-idea/SKILL.md` step 2 and the directory description refer to `idea-organization` instead of restating the layout and metadata.

## 4. Contracts and integration points

### 4.1 Template variables

| Template | Variables |
|----------|-----------|
| `brainstorm-idea.md` | `IDEA_DIRECTORY` |
| `create-spec.md` | `IDEA_DIRECTORY` |
| `revise-spec.md` | `IDEA_DIRECTORY` |
| `create-implementation-plan.md` | `IDEA_DIRECTORY`, `PLAN_SKILLS` |
| `repair-plan.md` | `VALIDATION_ERRORS`, `PLAN_TEXT` (unchanged) |
| `revise-plan.md` | `IDEA_DIRECTORY` |

`IDEA_FILE`, `DISCUSSION_FILE`, `SPEC_FILE` and `PLAN_WITHOUT_STORIES_FILE` are removed from all templates and call sites.

### 4.2 Unchanged contracts

- create-plan and repair-plan still return the plan as Claude's final text. `create_plan.py` still validates it, runs one repair pass, and writes `plan_file` or `broken_plan_file`.
- `ClaudeCodeCommand` fields (`cwd`, `interactive`, `allowed_tools`, `session_id`) are unchanged at every call site.
- `src/i2code/implement/templates/*.j2` and the `design` and `improve` templates are unchanged.

### 4.3 Skill ↔ code consistency test

A pytest unit test (`tests/plugin-skills/test_idea_organization_skill.py`, a new directory, marker `unit`):

1. Reads `claude-code-plugins/idea-to-code/skills/idea-organization/SKILL.md`, finds the `## Idea files` table, and extracts the suffix after `<name>-` from each `File` cell.
2. Builds `IdeaProject("/tmp/x/x")`, takes every public property returning a path under the directory (all `*_file` properties), and extracts the suffix after `x-`. For `idea_file`, the suffix is `idea.md`.
3. Asserts the two sets are equal.

## 5. Plugin evals

### 5.1 Layout

```
claude-code-plugins/idea-to-code/evals/
  fixtures/eval-idea/                 # synthetic type-C idea directory
    eval-idea-idea.md
    eval-idea-discussion.md           # ends with ## Classification, **Type:** C. ...
    eval-idea-spec.md
    eval-idea-plan.md
    eval-idea-metadata.yaml
  skills/<case>/                      # skill-based variant
    prompt.md                         # generated by the render step, git-ignored
    case.yaml                         # scaffold copies the files the case needs
    graders/*.md
  baseline/<case>/                    # frozen before any template changes, committed
    prompt.md
    case.yaml
    graders/*.md
  baseline-results/aggregate-result.json   # committed
```

The four cases are `create-spec`, `revise-spec`, `create-plan` and `revise-plan`. Each case's scaffold copies the fixture into the eval workspace at `docs/ideas/active/eval-idea/`. The prompt is rendered with `IDEA_DIRECTORY=docs/ideas/active/eval-idea`, a path relative to the workspace root, because the eval workspace root plays the role of the repository root.

### 5.2 Prompt rendering

`test-scripts/render_eval_prompts.py` (run as `uv run python test-scripts/render_eval_prompts.py <out-dir>`; kept out of `src/i2code` so it is not shipped in the wheel) builds each prompt by calling the real step function (`create_spec`, `revise_spec`, `create_plan`, `revise_plan`) on an `IdeaProject` for the fixture copy, with a capturing runner. The runner records the first `ClaudeCodeCommand.prompt` it receives and raises a private sentinel exception, which the script catches. The script then replaces the fixture's absolute directory in the prompt with `docs/ideas/active/eval-idea` and writes `<out-dir>/<case>/prompt.md` with the case's frontmatter.

For the interactive steps, the case prompt is the rendered prompt followed by a fixed request:

| Case | Appended request |
|------|------------------|
| `create-spec` | none |
| `revise-spec` | `Change the specification: add a non-functional requirement that an uncached badge response is returned in under 500 ms.` |
| `create-plan` | none |
| `revise-plan` | `Change the plan: add a task to the last steel thread that returns a grey `unknown` badge when the GitHub API rate limit is exceeded.` |

### 5.3 Graders

| Case | Graders |
|------|---------|
| `create-spec` | `file_exists` for `docs/ideas/active/eval-idea/eval-idea-spec.md` (the scaffold does not copy the spec for this case); `regex` on that file for each Platform Capability heading: `Purpose and context`, `Consumers`, `Capabilities`, `APIs, contracts, or integration points` (match any of `API`, `contract`, `integration`), `Non-functional`, `Scenarios`, `Constraints and assumptions`, `Acceptance criteria`; `llm` on that file: "Every decision point has a single answer; the document never offers 'X or Y' alternatives and contains no implementation plan." |
| `revise-spec` | `regex` on the spec file: `## Change History\s+(.|\n)*### \d{4}-\d{2}-\d{2}: ` |
| `create-plan` | on the final text: `regex` for `^## Idea Type`, `^## Instructions for Coding Agent`, and the line `- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0`; `regex` that every `TaskType:` line matches `TaskType: (OUTCOME|INFRA|REFACTOR)\s*$`; `llm`: "Every task block has TaskType, Entrypoint, Observable, Evidence and at least one step." |
| `revise-plan` | on the plan file: the same TaskType `regex` and `llm` task-block grader as create-plan; `regex` for `^## Change History` |

### 5.4 Running

`test-scripts/test-plugin-evals.sh`:

1. Checks that `claude` and `i2code` are on `PATH` (revise-plan's `plan-file-management` skill runs `i2code plan`). Exits 1 with a message if either is missing.
2. Renders the skill-based prompts into `claude-code-plugins/idea-to-code/evals/skills/`.
3. Runs `claude plugin eval` on the plugin with `--eval-dir` pointing at `evals/skills`, `--no-publish`, `--trust-plugin`, `--json`, `--allow-tools Read,Write,Edit,Glob,Grep,Bash,Skill`, `--max-cost-usd ${EVAL_MAX_COST_USD:-25}` and the default 3 runs. Output goes to `logs/plugin-evals/<timestamp>/`.
4. With `--baseline`, runs the same command on `evals/baseline` instead, and copies `aggregate-result.json` to `evals/baseline-results/`.
5. Exits with the eval command's exit code.

`claude-code-plugins/idea-to-code/evals/skills/*/prompt.md` is added to `.gitignore`.

The script is not called from `test-all.sh`, CI or pre-commit.

## 6. Non-functional requirements

- **Cost:** a full skill-based run is 4 cases × 3 runs = 12 sessions; with `--baseline` another 12. The run stops at `EVAL_MAX_COST_USD` (default 25).
- **Reliability gate:** each skill-based case passes 3 of 3 runs (threshold 1.0) before the reduced templates are committed.
- **Prompt size:** first-message size drops because no file is inlined with `@`.
- **No regression in i2code behaviour:** `./test-scripts/test-unit.sh` and `./test-scripts/test-integration.sh` pass; `uvx pyright --level error src/` reports no errors.

## 7. Scenarios and workflows

### 7.1 Primary end-to-end scenario: create-spec through a skill

1. The baseline suite exists: `evals/baseline/create-spec/prompt.md` was rendered from the current `create-spec.md` and committed with its baseline result.
2. A developer runs `i2code spec create docs/ideas/active/foo` (relative path, no `repo_root`).
3. `IdeaProject` stores the absolute directory. `create_spec` renders `create-spec.md` with that `IDEA_DIRECTORY`. The prompt has no `@` and names `idea-to-code:idea-organization` and `idea-to-code:write-spec`.
4. Claude, running in the idea directory, invokes both skills, reads `foo-idea.md` and `foo-discussion.md` by absolute path, reads `**Type:** C. Platform/infrastructure capability`, and writes `foo-spec.md` with the type-C sections.
5. `./test-scripts/test-plugin-evals.sh` passes the `create-spec` case 3 of 3.

### 7.2 Revise-spec records Change History

`i2code spec revise <idea>` renders `revise-spec.md`. The user asks for a change. Claude invokes `write-spec`, edits the spec and adds a `### YYYY-MM-DD:` entry under `## Change History`. Eval case `revise-spec` passes; its baseline case is expected to fail.

### 7.3 Create-plan with an invalid TaskType is repaired

Claude returns a plan with `TaskType: TEST`. `plan_validator.py` reports `Invalid TaskType 'TEST' in Task 2.1 (expected OUTCOME, INFRA or REFACTOR)`. The repair prompt names `plan-format`; the repaired plan passes and is written to `<name>-plan.md`.

### 7.4 Revise-plan keeps the format

`i2code plan revise <idea>` renders `revise-plan.md`. The user asks for a new task. Claude uses `plan-file-management` to insert it with `--task-type OUTCOME`, records the change under `## Change History`, and the plan still passes `plan_validator.py`. Eval case `revise-plan` passes.

### 7.5 Skill used outside i2code

In an ordinary Claude Code session, the user says "write the spec for docs/ideas/active/foo". Claude invokes `write-spec` and `idea-organization` from their descriptions and produces the same spec as in 7.1.

### 7.6 Discussion without a recorded type

create-spec runs on an older idea whose discussion has no `**Type:**` line. Claude tells the user the type is not recorded and asks which of A–D it is before writing the spec.

### 7.7 Skill and IdeaProject drift

A developer adds a `*_file` property to `IdeaProject` without updating the `## Idea files` table. `tests/plugin-skills/test_idea_organization_skill.py` fails and names the missing suffix.

## 8. Constraints and assumptions

- The eval suite is built and the baseline recorded **before** any template changes, so the baseline measures the current prompts.
- `claude plugin eval` details (case folder format, `case.yaml` scaffold, grader types, flags) come from the plugin-eval reference consulted during brainstorming. The exact flag names are confirmed with `claude plugin eval --help` when the script is written.
- The pre-commit plugin validation added in 2b76819 (Validate the idea-to-code plugin in pre-commit and remove obsolete commands) must accept the new `skills/*` entries and the `evals/` directory.
- The fixture is synthetic and small, so eval runs stay cheap. It is not a copy of a real idea.
- brainstorm-idea has no eval in the first suite, because brainstorming is multi-turn and the eval tool runs single prompts.
- The unit tests that check prompt wiring (`tests/idea-cmd/test_brainstorm.py:162`, `tests/spec-cmd/test_create_spec.py:50`, `tests/spec-cmd/test_revise_spec.py:66`, `tests/go-cmd/test_create_plan.py:145`, `tests/go-cmd/test_revise_plan.py:77`) are updated, not removed: they assert the rendered template name, that `project.directory` appears in the prompt, that the expected skill names appear, and that `@` does not.
- A new unit test covers `IdeaProject` given a relative path: `directory` and every derived path are absolute.

## 9. Out of scope

- Changing the content of the Instructions for Coding Agent block.
- `src/i2code/implement/templates/*.j2` and the `design` and `improve` templates.
- Recording the idea type in `<name>-metadata.yaml`.
- Running the evals in CI or pre-commit.
- An eval for brainstorm-idea.

## 10. Acceptance criteria

1. `idea-organization`, `brainstorm-idea`, `write-spec`, `create-plan` and `plan-format` exist under `claude-code-plugins/idea-to-code/skills/` and are listed in `plugin.json`.
2. The idea types A–D are defined only in `idea-organization`. A search of `src/i2code/prompt-templates/` for `Architecture POC` finds nothing.
3. The plan task format is defined only in `plan-format`. `repair-plan.md` and `create-implementation-plan.md` no longer contain `TaskType: OUTCOME | INFRA | REFACTOR`.
4. The planning method is defined only in `create-plan`. `create-implementation-plan.md` no longer contains `## General principles` or `## Task 1.1 Requirements`.
5. No template in 3.5 contains `@`.
6. `revise_spec.py` renders `revise-spec.md` instead of building the prompt inline.
7. `plan_validator.py` rejects a TaskType outside OUTCOME, INFRA, REFACTOR. `task_cli.py` help and `plan-file-management` say OUTCOME, INFRA or REFACTOR.
8. `IdeaProject.directory` is absolute for a relative argument.
9. `tests/plugin-skills/test_idea_organization_skill.py` passes and fails when a row or property is removed.
10. `evals/baseline/` and `evals/baseline-results/aggregate-result.json` are committed from a run made before the templates changed.
11. `./test-scripts/test-plugin-evals.sh` passes every skill-based case 3 of 3.
12. `./test-scripts/test-unit.sh` and `./test-scripts/test-integration.sh` pass, and `uvx pyright --level error src/` reports no errors.

## Change History

### 2026-10-17: Move the planning method into a new `create-plan` skill

The first version kept the planning method (Implementation context, Analyze existing code, General principles, Task 1.1 Requirements, Goal) in `create-implementation-plan.md`. Section 3.6 now defines a `create-plan` skill that contains it. Sections 1, 2, 3.5, 9 and 10 are updated to match.

Rationale: keeping the method in the template contradicted Q8 (skills work in an ordinary Claude Code session) and the Goal (templates reduced to the idea directory, the skills and i2code mechanics). The user chose the name `create-plan` to match the i2code step.


### 2026-10-17: Replace the revise-spec and revise-plan eval requests with changes to the badge service

Section 5.2's appended requests asked for a requirement on the cost of an eval run and a task for a README section about running the evals. Neither relates to the eval fixture, a build status badge service. In the revise-spec eval, Claude asked what "eval run" meant instead of editing the spec, so the case scored 0 whatever the prompt said. The requests now ask for a 500 ms limit on an uncached badge response, and for a task that returns a grey `unknown` badge when the GitHub API rate limit is exceeded.
