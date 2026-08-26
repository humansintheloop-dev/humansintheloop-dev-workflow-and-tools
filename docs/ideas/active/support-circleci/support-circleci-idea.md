## Support CircleCI (and future CI providers)

### Motivation

Some projects, such as https://github.com/eventuate-tram/eventuate-tram-core, use CircleCI for continuous integration rather than GitHub Actions. The `i2code` tool's CI integration (waiting for builds, fetching failure logs, auto-fixing failures) currently only supports GitHub Actions. This prevents `i2code` from working with CircleCI-based projects.

### Goal

Introduce a generic CI provider abstraction and implement CircleCI as the second provider, so `i2code` can detect which CI system a project uses and interact with it accordingly.

### Key Design Decisions

1. **Generic abstraction**: Define a `CIProvider` protocol with methods for listing runs, fetching per-job failure logs, and waiting for completion. GitHub Actions becomes the first implementation; CircleCI becomes the second.

2. **CI/PR separation**: Extract CI-specific methods out of `GitHubClient` into the `CIProvider` protocol. PR operations stay on `GitHubClient` (code is always hosted on GitHub).

3. **Lazy detection**: A `LazyDetectingCIProvider` proxy starts with `NoCIProvider` (skip-CI behavior) and checks for CI config files on each call. When `.github/workflows/*.yml` or `.circleci/config.yml` appears (even mid-session, e.g., created during scaffolding), it upgrades to the real provider. Single provider per project; fail with a clear error if both are detected.

4. **CircleCI specifics**:
   - Auth via `CIRCLECI_TOKEN` in `.env.local`
   - Project slug auto-derived from git remote URL
   - Track Pipelines as the unit of "a CI run"
   - Use v2 API as primary, v1.1 as fallback for log retrieval

5. **Per-job log structure**: The protocol returns failure logs as `(job_name, log_text)` pairs, not a single concatenated string. Both providers benefit from this granularity.

6. **Artifact retrieval**: The protocol includes methods for listing and downloading build artifacts (especially JUnit XML test reports). This is a new capability — the current build fixer only uses console logs. Artifacts contain richer information (full stack traces, container logs) that improve fix accuracy.

7. **Injection**: CIProvider is passed directly to consumers (monitor, build fixer, review processor, scaffolder) rather than hung on GitRepository.

8. **Provider-owned polling**: Each provider implements its own `wait_for_completion()` polling strategy.

### Package Structure

New top-level package `i2code/ci/` with subpackages:
- `i2code/ci/common/` — CIProvider protocol, shared types (run result, job log, artifact), detection logic
- `i2code/ci/github/` — GitHub Actions provider implementation (extracted from `GitHubClient`)
- `i2code/ci/circleci/` — CircleCI provider implementation (new, REST API-based)

### Affected Components

- `GitHubClient` — CI methods extracted into `GitHubActionsCIProvider`
- `GithubActionsMonitor` — generalized to `CIMonitor`, accepts `CIProvider`
- `GithubActionsBuildFixer` — generalized to `CIBuildFixer`, accepts `CIProvider`
- `ModeFactory` — detects CI provider, wires the correct implementation
- `PullRequestReviewProcessor` — updated to use `CIProvider` instead of `gh_client` for CI
- `ProjectScaffolder` — updated to use `CIProvider` instead of `gh_client` for CI
- `ci_fix.j2` template — updated to present per-job failure information
- `FakeGitHubClient` — CI methods extracted into `FakeCIProvider` for tests
- New: `CircleCICIProvider` — CircleCI REST API implementation with injectable HTTP client
