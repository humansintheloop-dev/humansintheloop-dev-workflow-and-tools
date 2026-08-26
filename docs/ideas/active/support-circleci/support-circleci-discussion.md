# Support CircleCI - Discussion

## Classification

**Category: C — Platform/infrastructure capability**

**Rationale:** This extends the existing CI integration layer (currently GitHub Actions only) to support multiple CI providers. It's infrastructure that enables the `i2code` tool to work across projects using different CI systems, not a user-facing feature in itself.

## Codebase Analysis (Pre-Discussion)

Current CI integration architecture:
- `GitHubClient` (`src/i2code/implement/github_client.py`) — wraps `gh` CLI for all GitHub interactions including CI
- `GithubActionsMonitor` (`src/i2code/implement/github_actions_monitor.py`) — polls/watches workflow runs until completion
- `GithubActionsBuildFixer` (`src/i2code/implement/github_actions_build_fixer.py`) — detects failures, fetches logs, invokes Claude to fix
- `ModeFactory` (`src/i2code/implement/mode_factory.py`) — wires up CI components
- `FakeGitHubClient` (`tests/implement/fake_github_client.py`) — test double
- CI fix prompt template: `src/i2code/implement/templates/ci_fix.j2`
- Skill: `claude-code-plugins/idea-to-code/skills/debugging-ci-failures/SKILL.md`

No abstract CI provider interface exists. GitHub-specific concepts (run_id, workflow names, `gh` CLI) are hardcoded throughout.

The CI flow: push commit -> wait for CI via polling -> check result -> if failed, fetch logs and invoke Claude -> loop.

Configuration in `ImplementOpts`: `skip_ci_wait`, `ci_fix_retries`, `ci_timeout`.

## Questions and Answers

### Q1: Scope — CircleCI only, generic abstraction, or detection-only first?

**Answer:** Generic abstraction. Introduce a CI provider protocol/interface, then implement CircleCI as the second provider (alongside GitHub Actions). Future providers slot in easily.

### Q2: Detection — How to determine which CI provider a project uses?

**Answer:** Auto-detect from config files. Check for `.circleci/config.yml` vs `.github/workflows/*.yml` in the repo. No explicit user config needed for detection.

### Q3: Authentication — How to provide CircleCI API token?

**Answer:** Store `CIRCLECI_TOKEN` in `.env.local`, consistent with existing secret handling. The project already loads `.env.local` via `dotenv` in `implement_command.py`.

### Q4: Multi-CI — What if a project has both GitHub Actions and CircleCI?

**Answer:** Single provider only. A project uses exactly one CI provider. If both config files are detected, fail with a clear error asking the user to specify which one to use.

### Q5: Architecture — How to separate CI concerns from PR concerns?

**Answer:** Split CI from PR. Extract CI-specific methods (`get_workflow_runs_for_commit`, `get_workflow_failure_logs`, `wait_for_workflow_completion`) into a `CIProvider` protocol. PR methods stay on `GitHubClient`. The current `GitHubClient` serves two roles: PR operations (always GitHub, since code is hosted there) and CI operations (varies by provider). The new `CIProvider` protocol would have two implementations: `GitHubActionsCIProvider` (wrapping `gh` CLI) and `CircleCICIProvider` (wrapping CircleCI REST API).

### Q6: CircleCI API version?

**Answer:** Both as needed. Use the v2 API as the primary interface, but fall back to v1.1 for specific operations not available in v2 (e.g., build output/logs).

### Q7: CircleCI run concept — what maps to a "CI run"?

**Answer:** Pipeline. Track the CircleCI Pipeline (triggered by a commit) as the unit of "a CI run". A pipeline succeeds only if all its workflows/jobs succeed. This is analogous to how we track GitHub Actions workflow runs per commit. The CIProvider protocol will use generic terms (e.g., "run" or "build") that map to Pipeline in CircleCI and Workflow Run in GitHub Actions.

### Q8: CircleCI project slug — how to identify the project?

**Answer:** Auto-derive from git remote. Parse `git remote get-url origin` to extract org/repo, then construct the CircleCI project slug (`github/<org>/<repo>`) automatically. No extra configuration needed.

### Q9: Failure log structure — single string or per-job?

**Discussion:** The current GitHub Actions implementation returns `--log-failed` as a single concatenated string, which loses structure. Even GitHub Actions has multiple jobs per workflow run. CircleCI similarly has jobs within workflows within pipelines. A single string is not a good model for either provider.

**Answer:** Per-job logs. The CIProvider protocol should return failure logs as a list of `(job_name, log_text)` pairs per run. Both GitHub Actions and CircleCI have job-level granularity. This gives Claude better context about which specific job failed and why. The CI fix template will be updated to present per-job information.

### Q10: Polling strategy — provider-owned or shared layer?

**Answer:** Provider implements polling. Each CIProvider implements `wait_for_completion()` with its own polling strategy. GitHub Actions can continue using `gh run watch`; CircleCI will poll its REST API. This keeps the protocol simple — each provider knows best how to efficiently wait for its own results.

### Q11: CIProvider injection — where to inject the CI provider?

**Answer:** Direct to consumers. Pass the CIProvider directly to the monitor and build fixer constructors, rather than hanging it on GitRepository. This is more explicit about dependencies and requires updating ModeFactory wiring, but keeps GitRepository focused on git operations and avoids coupling it to CI concepts.

### Q12: HTTP client for CircleCI API — approach?

**Discussion:** The CircleCI provider needs HTTP calls (unlike GitHub Actions which uses the `gh` CLI). User doesn't care about adding dependencies — key requirements are code maintainability and testability.

**Answer:** Use whatever HTTP library is simplest (e.g., `requests`). The important design constraint is that the HTTP layer must be injectable/mockable for testing, following the same pattern as `FakeGitHubClient`. The CircleCI provider should accept an HTTP client dependency so tests can substitute a fake without hitting the real API.

### Q13: Package structure — where does CI code live?

**Discussion:** The current CI code (`github_client.py`, `github_actions_monitor.py`, `github_actions_build_fixer.py`) lives in the flat `i2code/implement/` package alongside git, mode, and scaffolding code.

**Answer:** Create a top-level `i2code/ci/` package as a sibling to `implement`, with subpackages:
- `i2code/ci/common/` — CIProvider protocol, shared types (run result, job log, artifact), detection logic
- `i2code/ci/github/` — GitHub Actions provider implementation
- `i2code/ci/circleci/` — CircleCI provider implementation

The CI-specific methods currently on `GitHubClient` move into `i2code/ci/github/`. The monitor and build fixer generalize and move into `i2code/ci/common/` (or remain in `implement/` if they are more about orchestration than CI). `GitHubClient` in `implement/` retains only PR operations.

### Q14: Artifact retrieval — should the CIProvider protocol include artifact download?

**Discussion:** The current build fixer only fetches console logs (`--log-failed`), not uploaded artifacts like JUnit XML files. The debugging-ci-failures skill already documents artifact retrieval for both providers (GitHub Actions via `gh run download`, CircleCI via artifacts API), but the automated Python code doesn't use it. Adding artifact support to the protocol would be a *new capability*, not just a refactor of existing behavior.

Both GitHub Actions and CircleCI support uploading test artifacts (JUnit XML). These contain richer information than console logs: full stack traces, container/service logs, and root cause errors that are often truncated in console output.

**Answer:** Yes, include artifact retrieval in the CIProvider protocol. Methods for listing and downloading artifacts (especially JUnit XML test reports) should be part of the protocol. This allows the automated build fixer to provide Claude with structured test results, improving fix accuracy.

### Q15: Lazy detection — brand-new projects have no CI at startup

**Discussion:** For a brand-new project, there's initially no CI config. `i2code implement` may create CI files during scaffolding. One-time detection at startup would miss this and permanently treat the project as "no CI".

**Answer:** Use a `LazyDetectingCIProvider` proxy. It initially wraps a `NoCIProvider` (skip-CI behavior). On each CI method call, it checks for CI config files. When detected, it upgrades its delegate to the real provider permanently. This handles the case where CI files appear mid-session.

### Q16: Refactoring scope — which callers to update?

**Discussion:** Beyond `GithubActionsMonitor` and `GithubActionsBuildFixer`, two other places call CI methods on `gh_client` directly:
- `PullRequestReviewProcessor` (`pull_request_review_processor.py:370`) — calls `wait_for_workflow_completion`
- `ProjectScaffolder` (`project_scaffolding.py:91`) — calls `wait_for_workflow_completion`

**Answer:** Update all callers. Every place that calls CI methods should go through the CIProvider abstraction. No code should reach GitHub Actions CI methods directly. Clean, consistent separation.

### Q17: Any additional requirements or concerns?

**Answer:** No. Ready to proceed to specification.

