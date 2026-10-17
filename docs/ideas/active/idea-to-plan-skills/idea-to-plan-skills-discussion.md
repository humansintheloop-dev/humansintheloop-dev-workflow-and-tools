# Discussion: Move idea-to-plan prompt guidance into skills

## Codebase findings (before questions)

- `create-implementation-plan.md` already has a `## Skills to Follow` section filled from `${PLAN_SKILLS}` (`src/i2code/go_cmd/create_plan.py:64`), so the create-plan step already tells Claude to invoke plugin skills.
- `plan_validator.py` checks that TaskType, Entrypoint, Observable and Evidence are present, and that each task has steps. It does not check the TaskType value, so the `OUTCOME | INFRA | REFACTOR` vs `INFRA|OUTCOME` disagreement is not caught by Python.
- `src/i2code/plan_domain/plan.py:32` reads the idea type from the plan's `## Idea Type` section. It is the only Python code that knows about the idea type.
- `<name>-metadata.yaml` currently holds only `state` (written by `src/i2code/idea_cmd/brainstorm.py:71` and `write-idea`, read by `src/i2code/go_cmd/orchestrator.py:306`).
- `revise_spec.py:34` builds its prompt inline with plain paths (no `@`), so it is the one prompt that does not inline file contents.
- The `repair-plan.md` prompt receives the plan text and the validation errors, and returns the full plan on stdout. It runs in batch mode.

## Questions and answers

### Q1: Which idea type fits this work?

**Answer:** C. Platform/infrastructure capability.

### Q2: Where should the A–D idea type definitions live?

**Answer:** In `idea-organization`. It defines the four types and how an idea records its type. `write-spec` holds the per-type spec sections. `brainstorm-idea` and `plan-format` refer to `idea-organization` for the definitions. (Resolves open question 1.)

### Q3: Should brainstorm record the idea type in `<name>-metadata.yaml`?

**User:** What's wrong with it being in the discussion file?

**Claude:** Nothing, if the format is fixed. Today `brainstorm-idea.md` gives no heading or format for the classification. `create-spec.md:7` infers the type from the discussion prose, and `create-implementation-plan.md:28` infers it again from the spec. No Python code needs the type: `src/i2code/plan_domain/plan.py:32` reads it from the plan's `## Idea Type` section. Metadata would only help if Python needed it.

**Answer:** Keep it in the discussion file with a fixed format. `idea-organization` defines a `## Classification` section containing a `**Type:** <letter>. <name>` line (for example `**Type:** C. Platform/infrastructure capability`) followed by the rationale. Brainstorm writes it. create-spec and create-plan read that line instead of inferring the type. Metadata keeps only `state`. (Resolves open question 2.)

**Derived:** `create-implementation-plan.md` today references only the idea and spec files. Because the type is read from the discussion file, the create-plan step also needs the discussion file. The idea-directory approach gives it that.

### Q4: What happens to the "Instructions for Coding Agent" block that every plan copies?

Context: the plan reaches the coding agent through `src/i2code/implement/templates/task_execution.j2`, which inlines the whole plan with `@` and already says "Follow the active TDD and plan-tracking skills". The block's TDD rules are Java-specific.

**Answer:** Keep it, owned by `plan-format`. `plan-format` contains the block and says it is copied verbatim into every plan. Content unchanged, so plans still work when run outside i2code. (Resolves open question 3.)

### Q5: Which TaskType values are valid?

Context: `create-implementation-plan.md` defines OUTCOME, INFRA and REFACTOR. `plan-file-management` and the `--task-type` help text (`src/i2code/plan/task_cli.py:19`) say INFRA or OUTCOME. No Python code checks the value.

**Answer:** All three. `plan-format` defines OUTCOME, INFRA and REFACTOR. `plan-file-management` and the `task_cli.py` help text are corrected. `plan_validator.py` rejects any other value, so the existing repair-plan pass fixes it.

### Q6: How does `idea-organization`'s file list stay in step with `IdeaProject`?

Context: `file_patterns` (`src/i2code/implement/idea_project.py:96`) lists 4 files, but `IdeaProject` has path properties for 13.

**Answer:** A unit test. A pytest test reads a file-name table in the skill and checks that it matches the suffixes of `IdeaProject`'s path properties. A change to either side without the other fails the build. (Resolves open question 4.)

**Default assumption (changeable):** the skill's table lists every file `IdeaProject` knows about, with a column saying who writes it. Files only i2code writes (`sessionID.txt`, `wt-state.json`, `broken-plan.md`, `implement-config.yaml`) are marked as not to be edited by Claude. The test compares the full set.

### Q7: How should the relative idea path problem be handled?

Context from the code: `i2code go` passes `repo_root` (`src/i2code/go_cmd/orchestrator.py:150`–`176`), so Claude runs from the repo root and relative paths work. Bare idea names resolve to absolute paths (`src/i2code/idea/resolver.py:36`). The failure is only the standalone commands (`src/i2code/idea_cmd/cli.py:33`, `src/i2code/spec_cmd/cli.py:23` and `:32`, `src/i2code/plan/cli.py:40` and `:49`) given a relative path such as `docs/ideas/active/x`. They pass no `repo_root`, so Claude runs in the idea directory and the prompt's relative paths point nowhere. The new prompts name the idea directory, so they have the same exposure.

**Answer:** Fix it as part of this work. The new prompts pass the idea directory as an absolute path (`IdeaProject` normalizes it). One test covers a relative path argument with no `repo_root`. (Resolves open question 5.)

### Q8: Should the four skills also work in an ordinary Claude Code session, outside i2code?

**Answer:** Yes, self-contained. Each skill has a trigger description and works from just an idea directory. The i2code prompts add only i2code mechanics (stdout output, validation errors to repair). Evals can test a skill on its own.

**Derived:** `write-idea` (`claude-code-plugins/idea-to-code/skills/write-idea/SKILL.md:9`) refers to `idea-organization` for the directory layout and metadata instead of restating them.

### Q9: Which behaviours should the first eval suite check?

Context: `claude plugin eval` (checked via the plugin-eval reference) runs single batch prompts in a throwaway workspace, 3 runs per case by default. Graders are `regex`, `file_exists`, `tool_used`, `tool_order`, `llm` (judge rubric) and `baseline`, and regex/llm graders can read files Claude writes. Suites live in `evals/` under the plugin root. It does not drive interactive sessions, so the interactive steps are tested as batch cases: a fixture idea directory plus a prompt that states the request.

**Answer:** All four:

1. **create-spec shape** — given an idea and a discussion with `**Type:** C`, the spec file exists, has the Platform Capability Specification sections, and an LLM judge finds no "X or Y" choices left open.
2. **revise-spec Change History** — given an existing spec and a requested change, the spec gets a `### YYYY-MM-DD: ...` entry under `## Change History`. The baseline (today's inline prompt) is expected to fail.
3. **create-plan format** — the plan passes the `plan_validator.py` rules (fields present, TaskType one of OUTCOME/INFRA/REFACTOR) and contains the Instructions for Coding Agent block verbatim.
4. **revise-plan format** — given a plan and a requested change, the revised plan still passes the task format checks. The baseline (today's `revise-plan.md`) has no format rules.

Each case runs against the current template prompt (baseline) and the skill-based prompt.

**Default assumption (changeable):** brainstorm-idea gets no eval in the first suite, because brainstorming is a multi-turn conversation and the eval tool runs single prompts.

### Q10: When should the evals run?

**Answer:** Manually. A script under `test-scripts/` runs the suite with `--no-publish` and a `--max-cost-usd` ceiling. A developer runs it when a skill or template changes. It is not part of CI or pre-commit. (A full run is about 24 sessions: 4 cases × 2 prompt variants × 3 runs.)

### Q11: How does each eval case get its prompt?

**Answer:** The eval script renders each case's prompt with i2code's own template code, so the evals test the prompt i2code sends. Before the templates change, the rendered baseline prompts are saved as frozen files in the eval suite and the baseline results are committed.

**Default assumption (changeable):** the fixtures are one small synthetic type-C idea directory (idea, discussion, spec, plan) written for the evals, not a copy of a real idea.

### Q12: What result must the skill-based prompts reach before the reduced templates replace the current ones?

**Answer:** Every case passes all 3 runs with the skill-based prompt (the eval tool's default threshold of 1.0). The baseline result is recorded but is not a gate. The revise cases are expected to fail the baseline.

### Derived conclusions (no question needed)

- **Prompts stop using `@`.** Each reduced template names the idea directory (absolute, per Q7) and the skills to use. Claude reads the files it needs, so a file the step writes is no longer inlined on the first run or duplicated on resume.
- **i2code mechanics stay in the templates.** For example: create-plan's "output the plan to stdout, do not write files"; repair-plan's validation errors and plan text; brainstorm's "ask the final question, record the answer, then stop".
- **`brainstorm-idea` contains the question-and-answer process** (analyse the codebase first, one question at a time, append each Q&A immediately, use AskUserQuestion for multi-choice, write the `## Classification` section). Because it is self-contained (Q8), it works without the i2code template.
- **`revise_spec.py:34` moves its inline prompt into a `revise-spec.md` template** like the other steps, so it can name `write-spec` the same way.
- **The prompt-wiring unit tests are updated**, not removed: they check that the reduced template names the idea directory and the skills.

### Q13: Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?

**Answer:** No. The derived conclusions above stand as written.

### Q14 (after the first spec): Where does the planning method in `create-implementation-plan.md` go?

Context: the first spec kept the planning method (Implementation context, Analyze existing code, General principles, Incremental build-up, Task 1.1 Requirements, Goal) in the template. Brainstorming had not decided this. Keeping it contradicts Q8 (skills work in an ordinary session) and the Goal (templates reduced to the idea directory, the skills and i2code mechanics).

**User:** Why not call the skill create-plan?

**Answer:** A fifth skill, `create-plan`, contains the planning method. The name matches the i2code step that uses it. create-plan names `idea-organization`, `create-plan` and `plan-format`. revise-plan and repair-plan name only `plan-format`, since they change an existing plan.

## Classification

**Type:** C. Platform/infrastructure capability

**Rationale:** The consumers are the i2code steps (brainstorm, create-spec, revise-spec, create-plan, revise-plan, repair-plan). The deliverable is shared guidance, packaged as skills, that all of them use. No new user-visible command is added.
