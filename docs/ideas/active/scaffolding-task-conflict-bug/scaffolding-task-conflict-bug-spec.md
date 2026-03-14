# Scaffolding-Task Conflict Bug — Specification

## Purpose and Background

When `i2code implement` runs on a new project, it executes two sequential phases:

1. **Scaffolding** — `ScaffoldingCreator.run_scaffolding()` invokes Claude to create minimal project infrastructure (build files, CI workflow, placeholder code)
2. **Task execution** — `TrunkMode._execute_task()` invokes Claude to implement each plan task sequentially

A bug exists where these two phases produce conflicting CI workflow files. The scaffolding template (`scaffolding.j2:13`) instructs Claude to create `.github/workflows/ci.yaml`, while the hello-world plan (`hello-world-plan.md:67`) instructs Claude to create `.github/workflows/ci.yml`. Task execution has no awareness of what scaffolding already created, so Claude creates a second file with a different extension.

The goal of this idea is to **reproduce the bug with an automated test**, not to fix it.

## Target Users

- i2code developers who need a regression test for this bug
- Future developers working on a fix for the scaffolding-task coordination problem

## Problem Statement

There is no automated test that demonstrates the scaffolding-task conflict. The bug was observed manually but needs a reproducible test case to:

1. Confirm the bug exists
2. Serve as a regression test once a fix is applied

## Goals

- Write a `@pytest.mark.manual` test that reproduces the scaffolding-task CI file conflict
- The test should call real Claude (non-interactive mode) to exercise the actual scaffolding and task execution paths
- The final assertion (`ci.yml` does NOT exist) should **fail**, demonstrating the bug

## In Scope

- Copying hello-world idea fixtures into the test directory (at development time)
- A single test function that runs scaffolding then task execution and asserts the conflict
- Using lower-level APIs (`ScaffoldingCreator`, `CommandBuilder`, `ClaudeRunner`) rather than full `TrunkMode` wiring

## Out of Scope

- Fixing the bug (extension mismatch or scaffolding awareness)
- Testing other scaffolding-task conflicts beyond CI workflow files
- Interactive mode testing
- GitHub integration (no PR creation, no CI wait)

## Functional Requirements

### FR-1: Test Fixtures

The hello-world idea files are already available in `tests/implement/fixtures/hello-world/` (copied from the i2code-test-repo-hello-world example repo). The following files are required:

- `hello-world-idea.txt`
- `hello-world-spec.md`
- `hello-world-plan.md`
- `hello-world-discussion.md`

These files are checked into git as test fixtures.

### FR-2: Test Setup

The test creates a temporary git repository:

1. `git init` a temp directory
2. Copy fixtures from `tests/implement/fixtures/hello-world/` into a `docs/features/hello-world/` subdirectory within the temp repo
3. `git add` and `git commit` all files

### FR-3: Scaffolding Phase

The test invokes scaffolding using the lower-level API:

1. Create a `CommandBuilder` instance
2. Create a `ClaudeRunner(interactive=False)` instance
3. Create a `ScaffoldingCreator(command_builder, claude_runner)` instance
4. Call `scaffolding_creator.run_scaffolding(idea_directory, cwd=temp_repo, interactive=False)`
5. Assert that `.github/workflows/ci.yaml` exists in the temp repo

### FR-4: Task Execution Phase

The test executes the first plan task:

1. Create an `IdeaProject(idea_directory)` and call `get_next_task()` to extract the first task
2. Build the task command via `CommandBuilder().build_task_command(idea_directory, task.print())`  with `TaskCommandOpts(interactive=False)`
3. Run it via `ClaudeRunner(interactive=False).run(cmd, cwd=temp_repo)`

### FR-5: Bug Assertion

After task execution:

1. Assert `.github/workflows/ci.yml` does **NOT** exist — this assertion is expected to **fail**, reproducing the bug
2. The test is tagged `@pytest.mark.manual` because it calls real Claude and is slow

## Non-Functional Requirements

### NFR-1: Test Isolation

The test must not depend on external state (no GitHub repos, no network beyond Claude API). It operates entirely on a local temp directory.

### NFR-2: Cleanup

The temp directory must be cleaned up after the test (use `tmp_path` fixture or equivalent).

### NFR-3: Test Marker

The test must be tagged `@pytest.mark.manual` so it is excluded from normal test runs. It requires Claude API access and takes significant time.

## Success Metrics

- The test runs to completion when invoked manually
- The final assertion (`ci.yml` does NOT exist) **fails**, confirming the bug is reproduced
- The test is excluded from normal `pytest` runs via the `manual` marker

## Scenarios Supporting a Steel-Thread Plan

### Primary Scenario: Reproduce the Scaffolding-Task CI File Conflict

1. Set up a temp git repo with hello-world idea fixtures
2. Run scaffolding (real Claude, non-interactive) — produces `ci.yaml`
3. Run first plan task (real Claude, non-interactive) — produces `ci.yml`
4. Assert the conflict: `ci.yml` should not exist but does

### Secondary Scenario: Scaffolding Creates Expected Output

A subset of the primary scenario — verify that scaffolding alone produces the expected `ci.yaml` file. This is step 2-3 of the primary scenario and serves as a sanity check before running task execution.
