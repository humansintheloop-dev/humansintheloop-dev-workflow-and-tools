# Scaffolding-Task Conflict Bug — Discussion

## Codebase Analysis

### Root Cause

The scaffolding template (`src/i2code/implement/templates/scaffolding.j2:13`) instructs Claude to:
> Create .github/workflows/ci.yaml

The plan for hello-world (`hello-world-plan.md:67`) instructs Claude to:
> Create `.github/workflows/ci.yml`

These are different file extensions (`.yaml` vs `.yml`). Task execution (`task_execution.j2`) has no mechanism to make Claude aware of what scaffolding already created, so Claude creates a duplicate CI file.

### Affected Flow

1. `i2code implement` runs scaffolding via `ProjectScaffolder.ensure_scaffolding_setup()` → `ScaffoldingCreator.run_scaffolding()` → Claude creates `ci.yaml`
2. Task loop in `TrunkMode.execute()` picks up the first plan task → Claude creates `ci.yml`, ignoring the existing `ci.yaml`
3. Result: two CI workflow files in `.github/workflows/`

### Two Issues Identified

1. **Extension mismatch** — scaffolding hardcodes `.yaml`, but plans/specs may use `.yml`
2. **No scaffolding awareness in task execution** — the task execution prompt does not tell Claude what scaffolding already created, so even with matching extensions, Claude might recreate or conflict with scaffolding output

---

## Classification

**Type: A. User-facing feature** (specifically, a bug reproduction)

**Rationale:** This is a bug in the user-facing `i2code implement` workflow where scaffolding and task execution produce conflicting files. The deliverable is a reproduction test that demonstrates the conflict. While the code under test is infrastructure (`ScaffoldingCreator`, `CommandBuilder`), the bug manifests in the user-facing workflow — a user running `i2code implement` ends up with duplicate CI files.

---

## Questions and Answers

### Q1: Scope of the fix

**Q:** What is the scope? (A) Reproduce only, (B) Reproduce + fix extension mismatch, (C) Reproduce + fix both issues, (D) Something else

**A:** A — Reproduce only. Write the `@pytest.mark.manual` test that asserts the conflict exists, no fix.

### Q2: How to invoke scaffolding and task execution

**Q:** Should the test (A) use `mock_claude` to simulate Claude, (B) call Claude for real (slow, non-deterministic, `@pytest.mark.manual`), or (C) bypass Claude and directly create files to assert the conflict?

**A:** B — Call Claude for real. This is why the test is tagged `@pytest.mark.manual`.

### Q3: Idea files — copy at dev time, not runtime

The idea files from the hello-world test repo should be copied into the project's test directory at development time (checked into git), not at test runtime. The test references them as fixtures.

(Derived from idea file — no question needed.)

### Q4: Claude execution mode

**Q:** Should the test run Claude in (A) interactive mode (requires human interaction) or (B) non-interactive mode (fully automated, just slow)?

**A:** B — Non-interactive mode. The test is automated; `@pytest.mark.manual` means it's slow and requires Claude API access, not that it requires human interaction.

### Q5: Test wiring level

**Q:** Should the test (A) wire up through `TrunkMode` (full end-to-end) or (B) call lower-level functions directly (`ScaffoldingCreator` + `CommandBuilder`/`ClaudeRunner`)?

**A:** B — Call lower-level functions directly. Simpler setup, still exercises the real Claude path.

### Q6: Test location and structure (derived)

Based on existing patterns (`tests/implement/test_triage_real_claude.py`), the test will go in `tests/implement/` with fixtures (the copied hello-world idea files) in `tests/implement/fixtures/hello-world/`. The test file will be `tests/implement/test_scaffolding_task_conflict.py`.

The test flow:
1. Create a temp directory, `git init`, copy fixtures into an idea subdirectory, commit
2. Call `ScaffoldingCreator.run_scaffolding()` in non-interactive mode — Claude creates `ci.yaml`
3. Assert `.github/workflows/ci.yaml` exists
4. Extract first task from plan via `IdeaProject.get_next_task()`
5. Build task command via `CommandBuilder.build_task_command()`, run via `ClaudeRunner`
6. Assert `.github/workflows/ci.yml` does NOT exist (this should fail — reproducing the bug)
