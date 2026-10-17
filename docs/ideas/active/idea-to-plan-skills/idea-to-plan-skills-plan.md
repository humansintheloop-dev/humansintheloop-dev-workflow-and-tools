# Implementation Plan: Idea-to-plan guidance as skills

## Idea Type

**C. Platform/infrastructure capability**: the work moves reusable prompt guidance into plugin skills that i2code steps and ordinary Claude Code sessions both use. It also adds an eval harness that measures Claude's output before and after the move.

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

## Overview

This is a Python project (uv, pytest) with a Claude Code plugin in `claude-code-plugins/idea-to-code/`. The build and CI already exist:

- `.github/workflows/ci.yml` runs ruff, pyright, shellcheck on `test-scripts/*.sh`, gitleaks and `./test-scripts/test-end-to-end.sh`.
- Pre-commit (`.pre-commit-config.yaml`) also runs `claude plugin validate --strict claude-code-plugins/idea-to-code`.

Implement every task using TDD: write the failing test first, then the code. Python unit tests use `@pytest.mark.unit`. `./test-scripts/test-verify-all-tests-have-markers.sh` fails on unmarked tests. The project test command is `./test-scripts/test-end-to-end.sh`. Before each commit, also run `uvx pyright --level error src/` and the CodeScene pre-commit safeguard (see `CODE_SCENE.md`).

Ordering constraint from the spec (section 8): the eval suite and the frozen baseline (Steel Thread 2) must be committed **before** any prompt template in `src/i2code/prompt-templates/` changes.

Eval runs call real Claude sessions and cost money. `./test-scripts/test-plugin-evals.sh` is run manually. It is never added to `test-end-to-end.sh`, `test-all.sh`, CI or pre-commit.

Decisions made at plan time:
- The eval script passes `--ablation none`. Without it, `claude plugin eval` adds a no-plugin arm by default, which doubles the 12 sessions the spec budgets.
- The eval script passes `--scaffold`, because `claude plugin eval` runs each case's `scaffold_script` only with that flag.
- The eval script passes `--output-dir logs/plugin-evals/<timestamp>`, so results go under `logs/` (already git-ignored) instead of `<plugin>/<eval-dir>/results/`.
- The unit test for the render script lives in `tests/plugin-evals/test_render_eval_prompts.py`. The skill consistency test lives in `tests/plugin-skills/test_idea_organization_skill.py`.

## Steel Thread 1: Existing build and CI pass

- [x] **Task 1.1: The existing test suite passes on master before any change**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: The script exits 0 and prints `=== All Tests Passed ===`
  - Evidence: Run `./test-scripts/test-end-to-end.sh` with output redirected to `logs/test-end-to-end.log` (per `idea-to-code:test-output-to-logfile`); it exits 0 and the log ends with `=== All Tests Passed ===`
  - Steps:
    - [x] Run `./test-scripts/test-end-to-end.sh` and confirm it exits 0
    - [x] Run `uvx pyright --level error src/` and confirm it reports no errors
    - [x] Run `claude plugin validate --strict claude-code-plugins/idea-to-code` and confirm it passes
    - [x] Confirm `.github/workflows/ci.yml` runs `./test-scripts/test-end-to-end.sh` in the `test` job. CI already exists, so do not create it

---

## Steel Thread 2: Eval suite and frozen baseline for the current templates

- [x] **Task 2.1: render_eval_prompts.py renders the four case prompts from the current templates**
  - TaskType: INFRA
  - Entrypoint: `uv run python test-scripts/render_eval_prompts.py <out-dir>`
  - Observable: The script writes `<out-dir>/create-spec/prompt.md`, `<out-dir>/revise-spec/prompt.md`, `<out-dir>/create-plan/prompt.md` and `<out-dir>/revise-plan/prompt.md`. Each file contains the prompt that the real step function (`create_spec`, `revise_spec`, `create_plan`, `revise_plan`) passed to Claude. The absolute fixture-copy directory is replaced by `docs/ideas/active/eval-idea`. The revise-spec and revise-plan prompts end with the fixed appended request from spec section 5.2. No Claude process is started.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/plugin-evals/test_render_eval_prompts.py -v -m unit`. The test runs the script with `subprocess` into a `tmp_path` and asserts the following for each of the four `prompt.md` files: it exists; it contains `docs/ideas/active/eval-idea`; it does not contain the temporary fixture-copy path; it contains the template marker (`create-spec` contains `Specification Quality Guidelines`, `create-plan` contains `## Task model`); `revise-spec` ends with `add a non-functional requirement that a full eval run costs at most USD 25.`; and `revise-plan` ends with `adds a README section describing how to run the evals.`
  - Steps:
    - [x] Write the failing test `tests/plugin-evals/test_render_eval_prompts.py` (marker `unit`) as described in Evidence
    - [x] Create the synthetic type-C fixture `claude-code-plugins/idea-to-code/evals/fixtures/eval-idea/` with these files: `eval-idea-idea.md`, `eval-idea-discussion.md` (ending with `## Classification`, `**Type:** C. Platform/infrastructure capability` and a `**Rationale:**` line), `eval-idea-spec.md`, `eval-idea-plan.md` (a small valid plan with one steel thread, two tasks using `TaskType: OUTCOME` and `TaskType: INFRA`, and a `## Change History` heading), and `eval-idea-metadata.yaml` (`state: draft`). Keep the files small and invented. Do not copy a real idea.
    - [x] Create `test-scripts/render_eval_prompts.py`. It copies the fixture into a temporary directory `.../docs/ideas/active/eval-idea`, builds `IdeaProject` on that copy, and calls each step function with a capturing runner. The runner's `execute()` records `command.prompt` and raises a private `_PromptCaptured` sentinel exception, which the script catches.
    - [x] Call `create_plan` with `PlanServices(template_renderer=render_template, plugin_skills_fn=list_plugin_skills, validator_fn=validate_plan)`. Call `revise_plan` with `render_template`.
    - [x] Replace the copy's absolute directory with `docs/ideas/active/eval-idea`, append the fixed requests for `revise-spec` and `revise-plan`, and write `<out-dir>/<case>/prompt.md`
    - [x] Write the case frontmatter that `claude plugin eval` expects at the top of `prompt.md`. First confirm the format by running `claude plugin eval init --bare scratch-case` inside a temporary plugin copy under `logs/`, and do not keep that output in the repo.
    - [x] Confirm `test-scripts/render_eval_prompts.py` is not in the wheel by running `./test-scripts/test-wheel-contents.sh` (it builds from `src/` only)

- [x] **Task 2.2: test-plugin-evals.sh runs the skill-based eval suite and writes results under logs/plugin-evals/**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-plugin-evals.sh`
  - Observable: With `claude` or `i2code` missing from `PATH`, the script exits 1 and prints which command is missing. Otherwise it renders prompts into `claude-code-plugins/idea-to-code/evals/skills/<case>/prompt.md` and runs `claude plugin eval` on `claude-code-plugins/idea-to-code` with these flags: `--eval-dir evals/skills --no-publish --trust-plugin --scaffold --ablation none --json --allow-tools Read,Write,Edit,Glob,Grep,Bash,Skill --max-cost-usd ${EVAL_MAX_COST_USD:-25}`, and `--output-dir logs/plugin-evals/<timestamp>`. It writes `logs/plugin-evals/<timestamp>/aggregate-result.json` with scores for the cases `create-spec`, `revise-spec`, `create-plan` and `revise-plan`, and exits with the eval command's exit code.
  - Evidence: Run `PATH=/usr/bin:/bin ./test-scripts/test-plugin-evals.sh`; it exits 1 with a missing-command message. Then run `./test-scripts/test-plugin-evals.sh`; the newest `logs/plugin-evals/<timestamp>/aggregate-result.json` exists, was created by this run, and lists all four cases. Then run `git status --porcelain claude-code-plugins/idea-to-code/evals/skills`; it shows no `prompt.md` files.
  - Steps:
    - [x] Create `claude-code-plugins/idea-to-code/evals/skills/<case>/case.yaml` for the four cases, one at a time (per `idea-to-code:incremental-development`). Each `scaffold_script` copies the fixture files the case needs into `docs/ideas/active/eval-idea/` in the workspace: `create-spec` gets idea, discussion and metadata (no spec); `revise-spec` and `create-plan` get idea, discussion, spec and metadata; `revise-plan` gets all five fixture files.
    - [x] Create the graders under `claude-code-plugins/idea-to-code/evals/skills/<case>/graders/` exactly as listed in spec section 5.3 (`file_exists`, `regex` and `llm` graders for each case)
    - [x] Create `test-scripts/test-plugin-evals.sh` (with `set -euo pipefail`, shellcheck clean): the PATH check, the render step (`uv run python test-scripts/render_eval_prompts.py claude-code-plugins/idea-to-code/evals/skills`), the `claude plugin eval` command with the flags above, and output to `logs/plugin-evals/<timestamp>/`
    - [x] Add `claude-code-plugins/idea-to-code/evals/skills/*/prompt.md` to `.gitignore`
    - [x] Run `claude plugin validate --strict claude-code-plugins/idea-to-code` and confirm the `evals/` directory passes the pre-commit plugin validation
    - [x] Do not add the script to `test-scripts/test-end-to-end.sh`, `test-scripts/test-all.sh` or `.github/workflows/ci.yml`

- [ ] **Task 2.3: test-plugin-evals.sh --baseline runs the frozen baseline suite and commits its aggregate result**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-plugin-evals.sh --baseline`
  - Observable: The script runs `claude plugin eval` with `--eval-dir evals/baseline` and the same flags, without re-rendering prompts. It copies the run's `aggregate-result.json` to `claude-code-plugins/idea-to-code/evals/baseline-results/aggregate-result.json`. The frozen prompts in `claude-code-plugins/idea-to-code/evals/baseline/<case>/prompt.md` contain the current templates' text, including `@` references and the inline idea types.
  - Evidence: Delete `claude-code-plugins/idea-to-code/evals/baseline-results/aggregate-result.json` if it exists, then run `./test-scripts/test-plugin-evals.sh --baseline`. The file is recreated and lists the four cases. `revise-spec` is expected to score below 1.0, so a non-zero exit code is recorded, not treated as a failure.
  - Steps:
    - [ ] Freeze the baseline: run `uv run python test-scripts/render_eval_prompts.py claude-code-plugins/idea-to-code/evals/baseline`, then copy each case's `case.yaml` and `graders/*.md` from `evals/skills/<case>/` into `evals/baseline/<case>/` one file at a time
    - [ ] Add the `--baseline` option to `test-scripts/test-plugin-evals.sh`: skip rendering, use `--eval-dir evals/baseline`, and copy `aggregate-result.json` to `evals/baseline-results/`
    - [ ] Run the baseline and commit `evals/baseline/` and `evals/baseline-results/aggregate-result.json` before any template in `src/i2code/prompt-templates/` changes
    - [ ] Record each baseline case's score in the commit message

---

## Steel Thread 3: The plan validator rejects TaskType values outside OUTCOME, INFRA and REFACTOR

- [ ] **Task 3.1: create-plan reports an invalid TaskType and passes it to the repair pass**
  - TaskType: OUTCOME
  - Entrypoint: `create_plan()` in `src/i2code/go_cmd/create_plan.py`, reached by `i2code plan create <idea-dir>`
  - Observable: A generated plan containing `TaskType: TEST` in Task 2.1 makes stderr print `PLAN_VALIDATION_ERROR: Invalid TaskType 'TEST' in Task 2.1 (expected OUTCOME, INFRA or REFACTOR)`. The repair prompt contains that error. When the repaired plan is valid, it is written to `<name>-plan.md`. A plan whose task types are only `OUTCOME`, `INFRA` and `REFACTOR` passes without repair.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/test_plan_validator.py tests/go-cmd/test_create_plan.py -v -m unit`. New tests: `validate_plan` on a plan with `TaskType: TEST` returns the exact error above; `validate_plan` accepts each of the three valid values; and `create_plan` with a `FakeClaudeRunner` that first returns a `TaskType: TEST` plan and then a valid plan issues a second call whose prompt contains `Invalid TaskType 'TEST' in Task 2.1`, then writes `project.plan_file`.
  - Steps:
    - [ ] Write the failing tests in `tests/go-cmd/test_plan_validator.py` and `tests/go-cmd/test_create_plan.py`
    - [ ] Add a `_VALID_TASK_TYPES` check to `_task_errors` in `src/i2code/go_cmd/plan_validator.py:17`, applied only when `task.task_type` is present (missing types keep the existing `Missing TaskType` error)
    - [ ] Change the `--task-type` help text in `src/i2code/plan/task_cli.py:19` to `Task type (OUTCOME, INFRA or REFACTOR)`
    - [ ] Replace every `--task-type <INFRA|OUTCOME>` in `claude-code-plugins/idea-to-code/skills/plan-file-management/SKILL.md` (lines 138, 148, 188) with `--task-type <OUTCOME|INFRA|REFACTOR>`
    - [ ] Grep the whole repository for `INFRA or OUTCOME` and `INFRA|OUTCOME` and fix every remaining occurrence in the same commit

---

## Steel Thread 4: IdeaProject stores an absolute directory

- [ ] **Task 4.1: A relative idea path gives absolute directory and file paths**
  - TaskType: OUTCOME
  - Entrypoint: `IdeaProject(directory)` in `src/i2code/implement/idea_project.py:18`, constructed by `i2code spec create docs/ideas/active/foo`
  - Observable: `IdeaProject("docs/ideas/active/foo").directory == os.path.abspath("docs/ideas/active/foo")`, `name == "foo"`, and every `*_file` property is an absolute path under that directory. `worktree_idea_project()` still maps the directory into the worktree.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/implement/test_idea_project.py -v -m unit`. A new test in `TestIdeaProjectConstruction` uses `monkeypatch.chdir(tmp_path)`, builds `IdeaProject("docs/ideas/active/foo")`, and asserts that `directory` and every `*_file` property satisfy `os.path.isabs`. The existing `TestWorktreeIdeaDirectory` tests still pass.
  - Steps:
    - [ ] Write the failing test in `tests/implement/test_idea_project.py`
    - [ ] Store `os.path.abspath(directory)` in `IdeaProject.__init__` (`src/i2code/implement/idea_project.py:19`)
    - [ ] Run `./test-scripts/test-unit.sh` and fix any test that compared `project.directory` with a relative path

---

## Steel Thread 5: idea-organization skill kept in step with IdeaProject

- [ ] **Task 5.1: The idea-organization skill's file table matches IdeaProject's file properties**
  - TaskType: OUTCOME
  - Entrypoint: `uv run --python 3.12 python3 -m pytest tests/plugin-skills/test_idea_organization_skill.py -v -m unit`
  - Observable: The test passes when the `## Idea files` table in `claude-code-plugins/idea-to-code/skills/idea-organization/SKILL.md` lists exactly the suffixes of IdeaProject's 12 `*_file` properties. It fails and names the missing suffix when a row or a property is removed.
  - Evidence: Run the Entrypoint; it passes. Then temporarily delete the `<name>-design.md` row from the skill table and run the Entrypoint again; it fails with a message containing `design.md`. Restore the row.
  - Steps:
    - [ ] Write the failing test `tests/plugin-skills/test_idea_organization_skill.py` (marker `unit`, per spec section 4.3). It parses the `## Idea files` table and extracts the suffix after `<name>-` from each `File` cell. It builds `IdeaProject("/tmp/x/x")`, takes every `*_file` property, and extracts the suffix after `x-`, mapping `idea_file` to `idea.md`. It asserts the two sets are equal and reports the set difference.
    - [ ] Create `claude-code-plugins/idea-to-code/skills/idea-organization/SKILL.md` with the frontmatter description from spec section 3.1. Its contents are: the directory layout; the lifecycle metadata (`state` values `draft`, `ready`, `wip`, `completed`, `abandoned`); the `## Idea files` table with columns `File`, `Purpose` and `Written by` and the 12 rows from spec section 3.1; the four idea types with one-paragraph definitions (`A. User-facing feature`, `B. Architecture POC`, `C. Platform/infrastructure capability`, `D. Educational/example repository`); and the `## Classification` / `**Type:** <letter>. <name>` recording rule. The recording rule includes this instruction: when the `**Type:**` line is missing, tell the user the type is not recorded and ask for it before continuing.
    - [ ] Add `./skills/idea-organization` to `skills` in `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`
    - [ ] Update `claude-code-plugins/idea-to-code/skills/write-idea/SKILL.md:9` and step 2 (`:17`) to refer to `idea-to-code:idea-organization` for the directory layout and metadata instead of restating them
    - [ ] Run `claude plugin validate --strict claude-code-plugins/idea-to-code`

---

## Steel Thread 6: create-spec through the write-spec skill

- [ ] **Task 6.1: i2code spec create renders a skill-based prompt with the absolute idea directory**
  - TaskType: OUTCOME
  - Entrypoint: `create_spec()` in `src/i2code/spec_cmd/create_spec.py`, reached by `i2code spec create docs/ideas/active/foo`
  - Observable: The prompt passed to Claude contains `project.directory`, `idea-to-code:idea-organization` and `idea-to-code:write-spec`, and does not contain `@`. Claude, given that prompt, writes `docs/ideas/active/eval-idea/eval-idea-spec.md` with the Platform Capability Specification sections. The `create-spec` eval case scores 1.0 (3 of 3 runs).
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/test_create_spec.py -v -m unit` passes. The updated `TestCreateSpecTemplateRendering` asserts `project.directory` is in the prompt, both skill names are in the prompt, and `"@" not in cmd.prompt`. Then `./test-scripts/test-plugin-evals.sh` produces a `logs/plugin-evals/<timestamp>/aggregate-result.json` in which `create-spec` scores 1.0.
  - Steps:
    - [ ] Update `tests/spec-cmd/test_create_spec.py:50` to the assertions above, and confirm the new tests fail
    - [ ] Create `claude-code-plugins/idea-to-code/skills/write-spec/SKILL.md` with the description and contents from spec section 3.3: inputs (read the type from the `**Type:**` line, following `idea-organization`); the four per-type section lists moved unchanged from `src/i2code/prompt-templates/create-spec.md:19`–`62`; naming; quality rules; and Change History rules
    - [ ] Add `./skills/write-spec` to `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`
    - [ ] Reduce `src/i2code/prompt-templates/create-spec.md` to: the idea directory `${IDEA_DIRECTORY}`, "Use `idea-to-code:idea-organization` and `idea-to-code:write-spec`", and "write the specification; do not write a plan"
    - [ ] Change `src/i2code/spec_cmd/create_spec.py:36` to pass only `{"IDEA_DIRECTORY": project.directory}`
    - [ ] Run `./test-scripts/test-plugin-evals.sh` and confirm `create-spec` scores 1.0. If it does not, revise the skill and template and rerun before committing.

---

## Steel Thread 7: revise-spec records Change History

- [ ] **Task 7.1: i2code spec revise renders revise-spec.md naming the write-spec skill**
  - TaskType: OUTCOME
  - Entrypoint: `revise_spec()` in `src/i2code/spec_cmd/revise_spec.py`, reached by `i2code spec revise <idea>`
  - Observable: The prompt is rendered from `revise-spec.md`. It contains `project.directory`, `idea-to-code:idea-organization`, `idea-to-code:write-spec` and `I will ask you to make changes to the specification`, and no `@`. Claude, asked for a change, adds a `### YYYY-MM-DD: ` entry under `## Change History`. The `revise-spec` eval case scores 1.0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/spec-cmd/test_revise_spec.py -v -m unit` passes. `TestReviseSpecPromptContent` (`tests/spec-cmd/test_revise_spec.py:61`) is replaced with tests that assert the strings above and `"@" not in cmd.prompt`. One test monkeypatches `render_template` to record the template name and asserts it is `revise-spec.md`. Then `./test-scripts/test-plugin-evals.sh` shows `revise-spec` at 1.0.
  - Steps:
    - [ ] Replace the `three files` and per-file-path tests in `tests/spec-cmd/test_revise_spec.py` with the tests above, and confirm they fail
    - [ ] Create `src/i2code/prompt-templates/revise-spec.md` with `${IDEA_DIRECTORY}`, the two skill names and `I will ask you to make changes to the specification`
    - [ ] Replace the inline prompt in `src/i2code/spec_cmd/revise_spec.py:35` with `render_template("revise-spec.md", {"IDEA_DIRECTORY": project.directory})`, and update the module docstring
    - [ ] Run `./test-scripts/test-plugin-evals.sh` and confirm `revise-spec` scores 1.0

---

## Steel Thread 8: create-plan through the create-plan and plan-format skills

- [ ] **Task 8.1: i2code plan create renders a skill-based prompt and the plan contains the Instructions block**
  - TaskType: OUTCOME
  - Entrypoint: `create_plan()` in `src/i2code/go_cmd/create_plan.py`, reached by `i2code plan create <idea-dir>`
  - Observable: The create prompt contains `project.directory`, `idea-to-code:idea-organization`, `idea-to-code:create-plan`, `idea-to-code:plan-format`, `## Skills to Follow` with the plugin skill list, and the stdout mechanics. It contains no `@`, `## General principles`, `## Task 1.1 Requirements`, `TaskType: OUTCOME | INFRA | REFACTOR` or `Architecture POC`. The plan Claude returns has `## Idea Type`, `## Instructions for Coding Agent` and the `Hard rule: NEVER git commit` line. Every `TaskType:` line is `OUTCOME`, `INFRA` or `REFACTOR`. The `create-plan` eval case scores 1.0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/test_create_plan.py -v -m unit` passes. `TestCreatePlanTemplateRendering` (`tests/go-cmd/test_create_plan.py:137`) asserts the included and excluded strings above against the prompt rendered by the real `render_template`. Then `./test-scripts/test-plugin-evals.sh` shows `create-plan` at 1.0.
  - Steps:
    - [ ] Update `tests/go-cmd/test_create_plan.py:137` with a test that uses the real `render_template` and asserts the strings above, and confirm it fails
    - [ ] Create `claude-code-plugins/idea-to-code/skills/plan-format/SKILL.md` per spec section 3.4. It contains: the plan skeleton (`# Implementation Plan:`, `## Idea Type`, `## Instructions for Coding Agent`, `## Overview`, steel threads, `## Change History`); the task model and task types moved from `src/i2code/prompt-templates/create-implementation-plan.md:207`–`275`; the steel thread heading format; the task structure; the rules moved from `:316`–`405`; the Instructions for Coding Agent block copied verbatim from `:426`–`456`, with the instruction that every plan contains it unchanged after `## Idea Type`; and the revision rules
    - [ ] Create `claude-code-plugins/idea-to-code/skills/create-plan/SKILL.md` per spec section 3.6. It contains: inputs (read the type from the discussion `**Type:**` line); the sections moved from `create-implementation-plan.md:39`–`203` and `:409`–`416` (Implementation context, Analyze existing code, General principles with Incremental build-up, Task 1.1 Requirements, Goal); and "the plan follows `plan-format`". It does not say where the plan is written.
    - [ ] Add `./skills/create-plan` and `./skills/plan-format` to `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`
    - [ ] Reduce `src/i2code/prompt-templates/create-implementation-plan.md` to: the idea directory `${IDEA_DIRECTORY}`, "Use `idea-to-code:idea-organization`, `idea-to-code:create-plan` and `idea-to-code:plan-format`", `## Skills to Follow` with `${PLAN_SKILLS}`, and the stdout mechanics now at `:12`–`15`
    - [ ] Change `src/i2code/go_cmd/create_plan.py:64` to pass `{"IDEA_DIRECTORY": project.directory, "PLAN_SKILLS": skills}`
    - [ ] Run `./test-scripts/test-plugin-evals.sh` and confirm `create-plan` scores 1.0

- [ ] **Task 8.2: The repair prompt names plan-format and no longer restates the task format**
  - TaskType: OUTCOME
  - Entrypoint: `create_plan()` in `src/i2code/go_cmd/create_plan.py` when the first plan fails validation
  - Observable: The second (repair) prompt contains `idea-to-code:plan-format`, the repair constraints, the validation errors and the plan text. It does not contain `TaskType: OUTCOME | INFRA | REFACTOR`. A repaired valid plan is written to `project.plan_file`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/test_create_plan.py -v -m unit`. A new test uses a `FakeClaudeRunner` that returns an invalid plan and then a valid plan, with the real `render_template`. It asserts the second call's prompt contains `idea-to-code:plan-format` and `Invalid TaskType 'TEST'`, does not contain `TaskType: OUTCOME | INFRA | REFACTOR`, and that `project.plan_file` holds the valid plan.
  - Steps:
    - [ ] Write the failing test in `tests/go-cmd/test_create_plan.py`
    - [ ] Reduce `src/i2code/prompt-templates/repair-plan.md` to: "Use `idea-to-code:plan-format`", the repair constraints (fix only the listed errors, no new threads, preserve numbering, resolve "X or Y" alternatives, full plan on stdout, no commentary), `$VALIDATION_ERRORS` and `$PLAN_TEXT`. Remove the restated task format at `:9`–`17`.

---

## Steel Thread 9: revise-plan keeps the task format

- [ ] **Task 9.1: i2code plan revise renders a skill-based prompt and the revised plan keeps the format**
  - TaskType: OUTCOME
  - Entrypoint: `revise_plan()` in `src/i2code/go_cmd/revise_plan.py`, reached by `i2code plan revise <idea>`
  - Observable: The prompt contains `project.directory`, `idea-to-code:idea-organization`, `idea-to-code:plan-format`, `idea-to-code:plan-file-management` and `I will ask you to make changes to the plan`, and no `@`. After Claude adds a task, the plan file still passes `validate_plan`, every `TaskType:` line is `OUTCOME`, `INFRA` or `REFACTOR`, and the plan has `## Change History`. All four skill-based eval cases score 1.0.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/go-cmd/test_revise_plan.py -v -m unit` passes. `TestRevisePlanTemplateRendering` (`tests/go-cmd/test_revise_plan.py:72`) uses the real `render_template` and asserts the strings above and the absence of `@`. Then `./test-scripts/test-plugin-evals.sh` exits 0, which means every case scored 1.0 at the default threshold.
  - Steps:
    - [ ] Update `tests/go-cmd/test_revise_plan.py:72` to the assertions above, and confirm the test fails
    - [ ] Reduce `src/i2code/prompt-templates/revise-plan.md` to `${IDEA_DIRECTORY}`, the three skill names and `I will ask you to make changes to the plan`
    - [ ] Change `src/i2code/go_cmd/revise_plan.py:30` to pass only `{"IDEA_DIRECTORY": project.directory}`
    - [ ] Run `./test-scripts/test-plugin-evals.sh`; it exits 0 with all four cases at 1.0
    - [ ] Add a README section that describes how to run `./test-scripts/test-plugin-evals.sh`, `--baseline` and `EVAL_MAX_COST_USD`

---

## Steel Thread 10: brainstorm through the brainstorm-idea skill

- [ ] **Task 10.1: i2code idea brainstorm renders a skill-based prompt with no inline idea types**
  - TaskType: OUTCOME
  - Entrypoint: `brainstorm_idea()` in `src/i2code/idea_cmd/brainstorm.py`, reached by `i2code idea brainstorm <idea-dir>`
  - Observable: The prompt contains `project.directory`, `idea-to-code:idea-organization` and `idea-to-code:brainstorm-idea`. It contains no `@` and no `Architecture POC`. `grep -r "Architecture POC" src/i2code/prompt-templates/` finds nothing, and no template listed in spec section 3.5 contains `@`.
  - Evidence: `uv run --python 3.12 python3 -m pytest tests/idea-cmd/test_brainstorm.py -v -m unit` passes. `test_claude_prompt_contains_idea_and_discussion_files` (`tests/idea-cmd/test_brainstorm.py:162`) is replaced by a test that asserts the strings above and the absence of `@` and `Architecture POC`. A new test in `tests/plugin-skills/test_prompt_templates.py` renders each of the six section-3.5 templates with `render_template` and asserts none contains `@` or `Architecture POC`.
  - Steps:
    - [ ] Update `tests/idea-cmd/test_brainstorm.py:162` and write `tests/plugin-skills/test_prompt_templates.py` (marker `unit`), and confirm they fail
    - [ ] Create `claude-code-plugins/idea-to-code/skills/brainstorm-idea/SKILL.md` with the description and contents from spec section 3.2. The process moves from `src/i2code/prompt-templates/brainstorm-idea.md:33`–`67`, with the idea types replaced by a reference to `idea-to-code:idea-organization` and the `## Classification` section written to the discussion file.
    - [ ] Add `./skills/brainstorm-idea` to `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`
    - [ ] Reduce `src/i2code/prompt-templates/brainstorm-idea.md` to `${IDEA_DIRECTORY}`, "Use `idea-to-code:idea-organization` and `idea-to-code:brainstorm-idea`", and "refine the idea in this directory"
    - [ ] Change `src/i2code/idea_cmd/brainstorm.py:83` to pass only `{"IDEA_DIRECTORY": project.directory}`
    - [ ] Grep `src/` and `tests/` for `IDEA_FILE`, `DISCUSSION_FILE`, `SPEC_FILE` and `PLAN_WITHOUT_STORIES_FILE` and remove every remaining use from the section-3.5 templates and their call sites
    - [ ] Run `./test-scripts/test-end-to-end.sh`, `uvx pyright --level error src/` and `claude plugin validate --strict claude-code-plugins/idea-to-code`, and confirm all pass

---

## Change History

### 2026-10-17: Task 2.2 eval cases differ from spec section 5.3

- The revise-plan Change History grader matches `^## Change History[ \t]*\n\s*\S` instead of `^## Change History`. The fixture plan already ends with an empty `## Change History` heading, so the spec's pattern passed even when the run added no entry.
- The two `complete-task-blocks` llm graders keep the spec's rubric sentence and add explicit PASS and FAIL conditions. With the bare sentence, the haiku judge voted FAIL on the unchanged fixture plan, whose task blocks are all complete.
- Each case's `case.yaml` sets `execution.timeout_seconds: 900` instead of the default 300, because single create-spec and create-plan runs took about 110 and 120 seconds. One create-spec run in the first full run still timed out at 900 seconds.
