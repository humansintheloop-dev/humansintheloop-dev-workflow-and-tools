# Testing with Claude - Discussion

## Codebase Analysis

### Current State

The project has one existing "real Claude" test: `test_triage_real_claude.py`, which:
- Is marked `@pytest.mark.manual` (manually invoked, not part of CI)
- Calls `ClaudeRunner.run_batch()` for the PR triage use case
- Uses fixture data (pr6_feedback.json) as input
- Prints prompt and response for manual inspection

All other tests use `FakeClaudeRunner` (a test double that returns canned `ClaudeResult` values).

### Callers of ClaudeRunner

**run_interactive() callers (8):**
1. `spec_cmd/create_spec.py` - generates spec from idea file
2. `spec_cmd/revise_spec.py` - revises spec interactively
3. `improve/update_claude_files.py` - reviews/updates project config
4. `improve/review_issues.py` - reviews GitHub issues
5. `setup_cmd/update_project.py` - pushes template updates
6. `idea_cmd/brainstorm.py` - brainstorms an idea
7. `design_cmd/create_design.py` - generates design doc
8. `go_cmd/revise_plan.py` - revises plan interactively

**run_batch() callers (5):**
1. `improve/analyze_sessions.py` - analyzes sessions
2. `improve/summary_reports.py` - generates summary reports
3. `implement/commit_recovery.py` - commits recovered changes
4. `implement/pull_request_review_processor.py` - triages PR review
5. `go_cmd/create_plan.py` - generates plan in batch mode

**run() callers (5, delegates to interactive or batch):**
1. `implement/project_scaffolding.py` - generates scaffolding
2. `implement/pull_request_review_processor.py` - fixes PR issues
3. `implement/trunk_mode.py` - executes task on branch
4. `implement/worktree_mode.py` - executes task via worktree
5. `implement/github_actions_build_fixer.py` - fixes CI failures

### Test Infrastructure
- `FakeClaudeRunner` supports `set_result()`, `set_results()`, `set_side_effect()`, records all calls
- `ClaudeResult` dataclass: returncode, CapturedOutput (stdout/stderr), DiagnosticInfo

## Questions and Answers

### Q1: What is the primary goal of these real-Claude tests?

Options:
- A. Prompt validation — catch prompt regressions
- B. Integration smoke tests — verify full pipeline end-to-end
- C. Output contract tests — verify Claude output matches expected formats
- D. Some combination

**Answer: B — Integration smoke tests.** Verify the full pipeline works end-to-end (command assembly, Claude invocation, output parsing).

### Q2: Scope — which callers?

(Derived from the idea file — not asked as a question.)

The idea explicitly scopes to `ClaudeRunner.run()` (which can be non-interactive) and `run_batch()` (which always is). The 8 `run_interactive()` callers are out of scope.

**In-scope callers (10):**

run_batch() callers (5):
1. `improve/analyze_sessions.py` - analyze_sessions()
2. `improve/summary_reports.py` - create_summary_reports()
3. `implement/commit_recovery.py` - TaskCommitRecovery.commit_uncommitted_changes()
4. `implement/pull_request_review_processor.py` - _run_triage()
5. `go_cmd/create_plan.py` - _generate_plan()

run() callers (5, forced non-interactive for testing):
1. `implement/project_scaffolding.py` - ScaffoldingCreator.run_scaffolding()
2. `implement/pull_request_review_processor.py` - _invoke_fix()
3. `implement/trunk_mode.py` - TrunkMode._run_claude()
4. `implement/worktree_mode.py` - WorktreeMode._run_claude()
5. `implement/github_actions_build_fixer.py` - GithubActionsBuildFixer._invoke_claude_for_fix()

### Q2: How to handle test setup?

Options:
- A. Fixture-based — canned input data only
- B. Live repo — real GitHub state
- C. Fixture-based for data, temp repo for git

**Answer: C.** Use fixture data for inputs (like pr6_feedback.json) but create temporary git repos for callers that need working directories with commits.
