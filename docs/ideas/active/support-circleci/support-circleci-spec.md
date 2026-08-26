# Platform Capability Specification: CI Provider Abstraction

## Purpose and Context

The `i2code` CLI tool automates the development loop: push code, wait for CI, detect failures, fetch logs, invoke Claude to fix, and repeat. This CI integration is currently hardcoded to GitHub Actions via the `GitHubClient` class in `src/i2code/implement/github_client.py`, which mixes CI operations (workflow runs, failure logs, polling) with PR operations (create PR, mark ready, fetch reviews).

Projects like [eventuate-tram-core](https://github.com/eventuate-tram/eventuate-tram-core) use CircleCI instead of GitHub Actions. The `i2code` tool cannot work with these projects because every CI operation assumes `gh` CLI commands and GitHub Actions data structures.

This capability introduces a `CIProvider` protocol that abstracts CI operations behind a provider-agnostic interface, with two concrete implementations: GitHub Actions and CircleCI. The code is always hosted on GitHub (PR operations remain on `GitHubClient`), but the CI system varies per project.

## Consumers

The following components within `i2code` consume CI operations and will depend on the `CIProvider` protocol:

| Consumer | Current CI access | CI operations used |
|----------|------------------|--------------------|
| `GithubActionsMonitor` (`github_actions_monitor.py`) | `gh_client` injected via constructor | `wait_for_workflow_completion` |
| `GithubActionsBuildFixer` (`github_actions_build_fixer.py`) | `git_repo.gh_client` | `get_workflow_runs_for_commit`, `get_workflow_failure_logs`, `wait_for_workflow_completion` |
| `PullRequestReviewProcessor` (`pull_request_review_processor.py:370`) | `git_repo.gh_client` | `wait_for_workflow_completion` |
| `ProjectScaffolder` (`project_scaffolding.py:91`) | `git_repo.gh_client` | `wait_for_workflow_completion` |
| `ModeFactory` (`mode_factory.py`) | Constructs `GithubActionsMonitor` with `git_repo.gh_client` | Wiring only |
| `CommandBuilder` (`command_builder.py`) | Receives `run_id`, `workflow_name`, `failure_logs` | Template rendering only |

After this work, all consumers receive a `CIProvider` instance directly via constructor injection. No consumer accesses CI operations through `git_repo.gh_client`.

## Package Structure

New top-level package `src/i2code/ci/` as a sibling to `src/i2code/implement/`:

```
src/i2code/ci/
    __init__.py
    common/
        __init__.py
        protocol.py        # CIProvider protocol, CIRun, JobLog, Artifact types
        detection.py        # LazyDetectingCIProvider, NoCIProvider, detect_ci_config()
    github/
        __init__.py
        provider.py         # GitHubActionsCIProvider — wraps `gh` CLI
    circleci/
        __init__.py
        provider.py         # CircleCICIProvider — wraps CircleCI REST API
        http_client.py      # Injectable HTTP client wrapper
```

Tests mirror this structure under `tests/ci/`.

## Capabilities and Behaviors

### Capability 1: CI Provider Protocol

A Python `Protocol` class defining the contract that all CI providers must implement.

**Protocol: `CIProvider`** (in `i2code/ci/common/protocol.py`)

Methods:

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_runs_for_commit` | `branch: str`, `sha: str` | `list[CIRun]` | List CI runs triggered by a specific commit on a branch |
| `get_failure_logs` | `run_id: str` | `list[JobLog]` | Fetch per-job failure logs for a failed run |
| `get_artifacts` | `run_id: str` | `list[Artifact]` | List downloadable artifacts for a run |
| `download_artifact` | `artifact: Artifact`, `dest_dir: str` | `Path` | Download an artifact to a local directory |
| `wait_for_completion` | `branch: str`, `sha: str`, `timeout_seconds: int` | `tuple[bool, CIRun \| None]` | Poll until all runs for the commit complete; return `(all_passed, first_failing_run)` |

**Data types** (in `i2code/ci/common/protocol.py`):

```python
@dataclass
class CIRun:
    run_id: str           # Provider-specific ID (GitHub: databaseId, CircleCI: pipeline ID)
    name: str             # Human-readable name (GitHub: workflow name, CircleCI: pipeline/workflow name)
    status: str           # "in_progress" | "completed"
    conclusion: str | None  # "success" | "failure" | None (while in progress)
    head_sha: str         # Commit SHA this run is for

@dataclass
class JobLog:
    job_name: str         # Name of the failed job
    log_text: str         # Console output for that job

@dataclass
class Artifact:
    name: str             # Artifact name (e.g., "test-reports")
    path: str             # Path within the artifact
    url: str              # Download URL (provider-specific)
```

Note: `run_id` is `str` (not `int`) because CircleCI uses UUIDs for pipeline IDs while GitHub Actions uses integer `databaseId` values.

### Capability 2: CI Provider Detection and Lazy Resolution

Brand-new projects start with no CI configuration. During `i2code implement`, Claude may create CI files (e.g., `.github/workflows/build.yml`) as part of scaffolding. A one-time detection at startup would miss this. Instead, detection is lazy — checked on every CI operation.

**Class: `LazyDetectingCIProvider`** (in `i2code/ci/common/detection.py`)

A proxy that implements the `CIProvider` protocol. It wraps a delegate that starts as a `NoCIProvider` and upgrades to a real provider when CI config files appear.

```python
class LazyDetectingCIProvider:
    """Proxy that re-detects the CI provider on each call.

    Starts with NoCIProvider (skip-CI behavior). On each method call,
    checks for CI config files. When detected, replaces the delegate
    with the appropriate provider for all subsequent calls.
    """

    def __init__(self, repo_root: str, provider_factory):
        self._repo_root = repo_root
        self._provider_factory = provider_factory
        self._delegate: CIProvider = NoCIProvider()
```

On each `CIProvider` method call, `LazyDetectingCIProvider`:
1. If `_delegate` is `NoCIProvider`, calls `_detect()` to scan for config files.
2. If CI config is found, replaces `_delegate` with the real provider (via `_provider_factory`). Once upgraded, detection stops — the delegate is permanent.
3. Forwards the call to `_delegate`.

**Class: `NoCIProvider`** (in `i2code/ci/common/detection.py`)

Implements `CIProvider` with skip-CI behavior:
- `get_runs_for_commit()` returns `[]`
- `get_failure_logs()` returns `[]`
- `get_artifacts()` returns `[]`
- `download_artifact()` raises `NotImplementedError`
- `wait_for_completion()` returns `(True, None)` (pretend CI passed — nothing to wait for)

**Detection function: `detect_ci_config`** (in `i2code/ci/common/detection.py`)

Pure detection logic used by `LazyDetectingCIProvider._detect()`:

| Condition | Result |
|-----------|--------|
| `.github/workflows/*.yml` exists, `.circleci/config.yml` does not | Return `"github"` |
| `.circleci/config.yml` exists, `.github/workflows/*.yml` does not | Return `"circleci"` |
| Both exist | Raise `CIDetectionError` |
| Neither exists | Return `None` |

**Provider factory:** `ModeFactory` passes a factory function to `LazyDetectingCIProvider` that maps `"github"` → `GitHubActionsCIProvider` and `"circleci"` → `CircleCICIProvider`. This keeps detection decoupled from provider construction.

### Capability 3: GitHub Actions Provider

**Class: `GitHubActionsCIProvider`** (in `i2code/ci/github/provider.py`)

Wraps the `gh` CLI for CI operations. Extracted from the current `GitHubClient` methods:

| Current `GitHubClient` method | Maps to `CIProvider` method |
|-------------------------------|----------------------------|
| `get_workflow_runs_for_commit(branch, sha)` | `get_runs_for_commit(branch, sha)` — converts JSON dicts to `CIRun` objects |
| `get_workflow_failure_logs(run_id)` | `get_failure_logs(run_id)` — parses `gh run view --log-failed` output into `JobLog` list (split by job headers) |
| `wait_for_workflow_completion(branch, sha, timeout)` | `wait_for_completion(branch, sha, timeout)` — retains `_poll_until_runs_appear` and `_watch_in_progress_runs` logic |
| *(new)* | `get_artifacts(run_id)` — wraps `gh run view <run_id> --json artifacts` |
| *(new)* | `download_artifact(artifact, dest_dir)` — wraps `gh run download <run_id> --name <name> --dir <dest>` |

Constructor: `GitHubActionsCIProvider(cwd: str)` — same `cwd` pattern as `GitHubClient` for `gh` CLI context.

After extraction, `GitHubClient` retains only PR operations: `find_pr`, `create_draft_pr`, `is_pr_draft`, `get_pr_state`, `get_pr_url`, `mark_pr_ready`, `fetch_pr_comments`, `fetch_pr_reviews`, `fetch_pr_conversation_comments`, `reply_to_review_comment`, `reply_to_pr_comment`, `fetch_failed_checks`, `get_resolved_review_comment_ids`, `get_default_branch`.

### Capability 4: CircleCI Provider

**Class: `CircleCICIProvider`** (in `i2code/ci/circleci/provider.py`)

Wraps the CircleCI REST API. Uses v2 API as primary, v1.1 as fallback for operations not available in v2.

Constructor: `CircleCICIProvider(project_slug: str, token: str, http_client=None)`

- `project_slug`: format `github/<org>/<repo>`, auto-derived from git remote URL
- `token`: `CIRCLECI_TOKEN` from environment (loaded via `.env.local`)
- `http_client`: injectable for testing; defaults to a `requests`-based implementation

**Concept mapping:**

| CIProvider concept | CircleCI concept | API |
|-------------------|-----------------|-----|
| CI run | Pipeline | v2: `GET /pipeline?org-slug=github/{org}` filtered by branch/SHA |
| Run status | Pipeline workflows' aggregate status | v2: `GET /pipeline/{id}/workflow` |
| Failure logs | Failed job step output | v2: `GET /workflow/{id}/job` then v1.1: `GET /project/github/{org}/{repo}/{build_num}/output/{step}/0` |
| Artifacts | Job artifacts | v1.1: `GET /project/github/{org}/{repo}/{build_num}/artifacts` |

**Polling strategy:** Poll `GET /pipeline/{id}/workflow` every 10-15 seconds until all workflows reach a terminal status (`success`, `failed`, `error`, `canceled`). A pipeline is considered failed if any workflow fails.

**Project slug derivation:** Parse `git remote get-url origin` to extract `<org>/<repo>`. Supports both HTTPS (`https://github.com/org/repo.git`) and SSH (`git@github.com:org/repo.git`) remote URL formats.

**HTTP client:** The `CircleCICIProvider` accepts an HTTP client dependency via its constructor. This allows tests to inject a fake HTTP client that returns canned responses, following the same testability pattern as `FakeGitHubClient`. The default implementation uses `requests` with:
- Base URL: `https://circleci.com/api/v2/` (v2) or `https://circleci.com/api/v1.1/` (v1.1)
- Auth header: `Circle-Token: <token>`

### Capability 5: Consumer Updates

All consumers that currently access CI through `git_repo.gh_client` are updated to receive a `CIProvider` via constructor injection.

**Generalized classes:**

| Current class | Generalized class | Change |
|--------------|-------------------|--------|
| `GithubActionsMonitor` | `CIMonitor` (in `i2code/ci/common/`) | Accepts `CIProvider` instead of `gh_client`. Same `skip_ci_wait`/`ci_timeout` config. |
| `GithubActionsBuildFixer` | `CIBuildFixer` (in `i2code/ci/common/`) | Accepts `CIProvider` instead of accessing `git_repo.gh_client`. Fetches per-job logs and artifacts. |
| `GithubActionsBuildFixerFactory` | `CIBuildFixerFactory` (in `i2code/ci/common/`) | Creates `CIBuildFixer` instances with the detected `CIProvider`. |

**Updated consumers (injection change only):**

| Consumer | Change |
|----------|--------|
| `PullRequestReviewProcessor` | Accepts `CIProvider` via constructor; calls `ci_provider.wait_for_completion()` instead of `gh_client.wait_for_workflow_completion()` |
| `ProjectScaffolder` / `ScaffoldingSteps` | Accepts `CIProvider` via constructor; calls `ci_provider.wait_for_completion()` instead of `gh_client.wait_for_workflow_completion()` |
| `ModeFactory` | Creates a `LazyDetectingCIProvider` with a provider factory; passes it to `CIMonitor`, `CIBuildFixer`, `PullRequestReviewProcessor`, and `ScaffoldingSteps` |

### Capability 6: CI Fix Template Update

The `ci_fix.j2` template (in `src/i2code/implement/templates/`) is updated to present per-job failure information and, when available, artifact-derived test results.

Current template variables: `workflow_name`, `run_id`, `failure_logs` (single string).

Updated template variables:

| Variable | Type | Description |
|----------|------|-------------|
| `run_name` | `str` | CI run name (generic, replaces `workflow_name`) |
| `run_id` | `str` | CI run ID (generic) |
| `job_logs` | `list[JobLog]` | Per-job failure logs |
| `test_reports` | `list[str]` | Contents of JUnit XML files from downloaded artifacts (empty if no artifacts) |

The `CommandBuilder.build_ci_fix_command` method signature updates to accept `run_name`, `run_id`, `job_logs`, and `test_reports` instead of the current `run_id`, `workflow_name`, `failure_logs`.

### Capability 7: Test Infrastructure

**`FakeCIProvider`** (in `tests/ci/fake_ci_provider.py`)

Test double implementing the `CIProvider` protocol with:
- `set_runs(runs: list[CIRun])` — configure canned run responses
- `set_failure_logs(run_id: str, logs: list[JobLog])` — configure canned logs
- `set_artifacts(run_id: str, artifacts: list[Artifact])` — configure canned artifacts
- `set_wait_result(success: bool, failing_run: CIRun | None)` — configure wait outcome
- `calls: list[tuple]` — record all method calls for assertion

The existing `FakeGitHubClient` is updated to remove CI methods. Tests that currently use `FakeGitHubClient` for CI operations are migrated to `FakeCIProvider`.

**`FakeHttpClient`** (in `tests/ci/circleci/fake_http_client.py`)

Test double for the CircleCI HTTP client. Accepts canned URL-to-response mappings so `CircleCICIProvider` can be tested without network calls.

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Testability** | All CI providers testable via injectable dependencies (fake clients). No real CI calls in unit tests. |
| **Maintainability** | Adding a new CI provider requires only: (1) a new subpackage under `i2code/ci/`, (2) a detection rule in `detection.py`, (3) a `FakeProvider` for tests. No changes to consumers. |
| **Backward compatibility** | Projects using GitHub Actions must work identically after the refactor. No change to CLI flags or `.env.local` variables for GitHub Actions users. |
| **Polling timeout** | Both providers respect `ci_timeout` (default 600s) from `ImplementOpts`. |
| **Error handling** | Missing `CIRCLECI_TOKEN` produces a clear error on first CI operation, not a cryptic API failure later. |
| **Log truncation** | Per-job logs are capped at 5000 characters each (matching the current behavior for the concatenated string). |

## Scenarios and Workflows

### Scenario 1 (Primary): CircleCI project — push, wait, detect failure, fix

A developer runs `i2code implement` on a project that has `.circleci/config.yml` and no `.github/workflows/`.

1. `ModeFactory` creates a `LazyDetectingCIProvider` and injects it into `CIMonitor`, `CIBuildFixer`, `PullRequestReviewProcessor`, and `ScaffoldingSteps`.
2. After Claude completes a task and commits, the code is pushed to the branch.
3. `CIMonitor.wait_for_completion()` calls `ci_provider.wait_for_completion(branch, head_sha, timeout)`.
4. `LazyDetectingCIProvider` detects `.circleci/config.yml`, upgrades its delegate to `CircleCICIProvider` (using `CIRCLECI_TOKEN` from environment and project slug derived from git remote), and forwards the call.
5. `CircleCICIProvider` polls `GET /api/v2/pipeline?org-slug=github/{org}&branch={branch}` to find the pipeline for the commit SHA, then polls workflow status until completion.
6. The pipeline fails. `CIMonitor` reports the failure.
7. `CIBuildFixer.check_and_fix_ci()` calls `ci_provider.get_runs_for_commit(branch, sha)` and finds a failed `CIRun`.
8. It calls `ci_provider.get_failure_logs(run_id)` which returns `list[JobLog]` — one entry per failed job, with logs fetched via CircleCI v1.1 API.
9. It calls `ci_provider.get_artifacts(run_id)` and `ci_provider.download_artifact()` to retrieve JUnit XML test reports.
10. `CommandBuilder` renders the updated `ci_fix.j2` template with per-job logs and test report contents.
11. Claude is invoked with the rendered prompt, analyzes the failure, and commits a fix.
12. The fix is pushed, and the cycle repeats (up to `ci_fix_retries` times).

### Scenario 2: GitHub Actions project — backward-compatible behavior

A developer runs `i2code implement` on a project with `.github/workflows/*.yml` and no `.circleci/config.yml`.

1. `ModeFactory` creates a `LazyDetectingCIProvider` (starting with `NoCIProvider` delegate).
2. On the first CI operation, `LazyDetectingCIProvider` detects `.github/workflows/*.yml` and upgrades to `GitHubActionsCIProvider`.
3. The flow proceeds identically to today, except CI operations go through the `CIProvider` protocol instead of directly through `GitHubClient`.
4. Failure logs are now returned as `list[JobLog]` (parsed from `--log-failed` output by splitting on job headers) instead of a single string.
5. Artifact retrieval is available as a new capability (JUnit XML download via `gh run download`).

### Scenario 3: Ambiguous CI configuration

A project has both `.github/workflows/*.yml` and `.circleci/config.yml`.

1. On the first CI operation, `LazyDetectingCIProvider._detect()` finds both config files.
2. Raises `CIDetectionError` with message: "Multiple CI systems detected (.github/workflows/ and .circleci/config.yml). Remove the unused CI configuration to proceed."

### Scenario 4: New project — no CI initially, CI added during scaffolding

A developer runs `i2code implement` on a brand-new project with no CI configuration.

1. `ModeFactory` creates a `LazyDetectingCIProvider` (starting with `NoCIProvider` delegate).
2. During scaffolding, Claude creates `.github/workflows/build.yml`.
3. After scaffolding commits are pushed, `CIMonitor.wait_for_completion()` is called.
4. `LazyDetectingCIProvider._detect()` finds the newly created `.github/workflows/build.yml`, upgrades to `GitHubActionsCIProvider`, and forwards the call.
5. From this point on, CI monitoring works normally.

### Scenario 4b: No CI configured and none added

A project has neither `.github/workflows/` nor `.circleci/config.yml`, and Claude does not create any CI files.

1. `LazyDetectingCIProvider` delegate remains `NoCIProvider` throughout the session.
2. All CI operations are no-ops: `wait_for_completion()` returns `(True, None)`, `get_runs_for_commit()` returns `[]`, etc.

### Scenario 5: Missing CircleCI token

A project has `.circleci/config.yml`. On the first CI operation, `LazyDetectingCIProvider` detects CircleCI and attempts to create a `CircleCICIProvider`.

1. `CIRCLECI_TOKEN` is not found in the environment.
2. The provider factory raises `CIConfigurationError` with message: "CircleCI detected but CIRCLECI_TOKEN is not set. Add it to `.env.local`."

## Constraints and Assumptions

- Code hosting is always GitHub. The PR operations on `GitHubClient` are not abstracted.
- A project uses exactly one CI provider. Dual-CI configurations are not supported; the user must remove the unused CI config.
- CircleCI authentication uses personal API tokens, not project-level tokens or OAuth.
- The CircleCI v2 API is the primary interface; v1.1 is used only for job step output and artifact retrieval where v2 lacks equivalent endpoints.
- GitHub Actions provider continues to use the `gh` CLI (requires `gh` to be installed and authenticated).
- The `debugging-ci-failures` skill (in `claude-code-plugins/`) already contains CircleCI instructions and does not need changes for this capability.

## Acceptance Criteria

1. **Lazy detection works**: `LazyDetectingCIProvider` starts with `NoCIProvider`, detects CI config files on first CI operation, and upgrades to the correct provider. Detection correctly handles GitHub Actions, CircleCI, both (error), and neither (stays as `NoCIProvider`).
2. **GitHub Actions parity**: All existing CI behavior (wait, detect failure, fetch logs, fix loop) works identically through the new `GitHubActionsCIProvider` as it did through `GitHubClient`.
3. **CircleCI end-to-end**: On a CircleCI-configured project, `i2code implement` can push code, wait for the pipeline, detect a failure, fetch per-job logs, download artifacts, and invoke Claude to fix — same as the GitHub Actions flow.
4. **Per-job logs**: Both providers return failure logs as `list[JobLog]` with job-level granularity. The CI fix template presents per-job information to Claude.
5. **Artifact retrieval**: Both providers can list and download build artifacts. The build fixer includes JUnit XML test report contents in the Claude prompt when artifacts are available.
6. **No consumer changes for new providers**: Adding a hypothetical third CI provider requires only a new subpackage under `i2code/ci/`, a detection rule in `detect_ci_config()`, and a factory mapping — no changes to `CIMonitor`, `CIBuildFixer`, `LazyDetectingCIProvider`, or any other consumer.
7. **Clean separation**: `GitHubClient` contains zero CI methods. No consumer accesses CI operations through `git_repo.gh_client`.
8. **Testable**: `FakeCIProvider` enables all existing tests to pass without real CI calls. `CircleCICIProvider` is tested via `FakeHttpClient` without network access.
9. **Clear errors**: Missing `CIRCLECI_TOKEN` and ambiguous CI detection produce actionable error messages on first CI operation.
10. **Late detection**: On a new project where CI files are created during scaffolding, `LazyDetectingCIProvider` detects the new CI config and upgrades from `NoCIProvider` to the appropriate provider without restart.

## Change History

### 2026-04-03: Replace one-time detection with lazy proxy pattern

Replaced `detect_ci_provider()` one-time startup detection with `LazyDetectingCIProvider` proxy. Brand-new projects start with no CI config; Claude may create CI files during scaffolding. One-time detection would miss this. The proxy starts with `NoCIProvider` and upgrades on first CI operation when config files appear. Removed `CI_PROVIDER` env var — ambiguous configurations require removing the unused CI config.
