Reproduce a bug where scaffolding and task execution create conflicting CI workflow files.

## Bug Description

When running `i2code implement --isolate --isolation-type nono` on a repository:

1. Scaffolding runs and creates `.github/workflows/ci.yaml` (as instructed by `scaffolding.j2:13`)
2. Task execution runs the first plan task, which creates `.github/workflows/ci.yml` — a different file extension
3. The task execution prompt has no awareness of what scaffolding already created, so Claude ignores the existing `ci.yaml`

## Test Fixtures

- Idea files are in `tests/implement/fixtures/hello-world/` (already copied from the i2code-test-repo-hello-world example repo)

## Reproduction Test

Write a Python test tagged with `@pytest.mark.manual` in `tests/implement/test_scaffolding_task_conflict.py` that:

1. Uses the hello-world idea files from `tests/implement/fixtures/hello-world/` (copied at dev time)
2. Creates a temp git repository containing those idea files
3. Calls `ScaffoldingCreator.run_scaffolding()` in non-interactive mode (real Claude)
4. Asserts that `.github/workflows/ci.yaml` is created
5. Extracts the first task from the plan via `IdeaProject.get_next_task()`
6. Runs the first task via `CommandBuilder.build_task_command()` + `ClaudeRunner`
7. Asserts that `.github/workflows/ci.yml` does NOT exist (this assertion should fail — reproducing the bug)

## Scope

Reproduce only. No fix in this idea.
