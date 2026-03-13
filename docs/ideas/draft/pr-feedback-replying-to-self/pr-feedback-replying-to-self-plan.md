The sandbox is restricting access to only the idea directory. I have enough context from the spec and discussion files to generate the plan. This is a Python project using `pytest`, with existing source in `src/i2code/` and the key files referenced in the spec.

Here's the implementation plan:

---

# Implementation Plan: PR Feedback Self-Reply Prevention

## Idea Type

**Type A — User-facing feature (bug fix)**

This is a bug fix to the existing `i2code implement --address-review-comments` feature that eliminates infinite self-reply loops and adds resolved conversation filtering.

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

- NEVER write production code (`src/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Steel Thread 1: Self-Comment Marker Prevents Reply Loops

This thread implements the primary defense against self-reply loops: all i2code replies are prefixed with `<!-- i2code -->`, and comments bearing this marker are filtered out during feedback processing. This is US-1.1 and US-1.2, covering Scenarios 1, 2, and 4 from the spec.

- [x] **Task 1.1: Fix replies include the `<!-- i2code -->` marker**
  - TaskType: OUTCOME
  - Entrypoint: `pytest` (run the test for `_push_and_reply`)
  - Observable: When `_push_and_reply` posts a reply comment, the body starts with `<!-- i2code -->\n` followed by the original reply content (e.g., `<!-- i2code -->\nFixed in abc12345`)
  - Evidence: Unit test mocks `GitHubClient.reply_to_review_comment` and asserts the body argument starts with `<!-- i2code -->\n`
  - Steps:
    - [x] Read `src/i2code/implement/pull_request_review_processor.py` to understand the current `_push_and_reply` method (spec references lines 277-302)
    - [x] Read existing tests for the processor to understand test patterns and fixtures
    - [x] Write a failing test that invokes `_push_and_reply` (or the code path that builds the reply body) and asserts the body starts with `<!-- i2code -->\n`
    - [x] Modify the reply body construction in `_push_and_reply` to prepend `<!-- i2code -->\n` before the existing content
    - [x] Verify the test passes
    - Implement using TDD

- [x] **Task 1.2: Clarification replies include the `<!-- i2code -->` marker**
  - TaskType: OUTCOME
  - Entrypoint: `pytest` (run the test for `_reply_with_clarifications`)
  - Observable: When `_reply_with_clarifications` posts a reply (both review comments and conversation comments), the body starts with `<!-- i2code -->\n` followed by the original clarification content
  - Evidence: Unit tests mock `GitHubClient.reply_to_review_comment` and `GitHubClient.reply_to_pr_comment`, assert the body argument starts with `<!-- i2code -->\n` for both code paths
  - Steps:
    - [x] Read `_reply_with_clarifications` in `src/i2code/implement/pull_request_review_processor.py` (spec references lines 179-200)
    - [x] Write a failing test for the review-comment clarification path asserting the marker prefix
    - [x] Write a failing test for the conversation-comment clarification path asserting the marker prefix (body format: `<!-- i2code -->\nRe: comment {id}\n\n{question}`)
    - [x] Modify the reply body construction in `_reply_with_clarifications` to prepend `<!-- i2code -->\n`
    - [x] Verify both tests pass
    - Implement using TDD

- [ ] **Task 1.3: Self-comments are filtered out during feedback processing**
  - TaskType: OUTCOME
  - Entrypoint: `pytest` (run the test for `_get_new_feedback` / `_fetch_unprocessed_feedback`)
  - Observable: When unprocessed comments are fetched and one has a body starting with `<!-- i2code -->`, that comment is excluded from the returned list and its ID is added to `WorkflowState.processed_comment_ids`
  - Evidence: Unit test provides a mix of user comments and `<!-- i2code -->`-prefixed comments; asserts only user comments are returned; asserts marker-bearing comment IDs are added to processed set
  - Steps:
    - [ ] Read `_get_new_feedback` (spec references `pull_request_review_processor.py:328-333`) and understand current filtering logic
    - [ ] Read `WorkflowState` to understand `processed_comment_ids` structure and how IDs are added
    - [ ] Write a failing test: provide unprocessed comments including one with body `<!-- i2code -->\nFixed in abc123`; assert it is filtered out and its ID is marked processed
    - [ ] Add marker-based filtering after the existing processed-ID filter in the processing pipeline
    - [ ] Ensure filtered comments are marked as processed in `WorkflowState`
    - [ ] Verify the test passes
    - Implement using TDD

- [ ] **Task 1.4: User comments in the same thread as i2code replies are still processed**
  - TaskType: OUTCOME
  - Entrypoint: `pytest`
  - Observable: When a thread contains both an i2code reply (with `<!-- i2code -->` marker) and a subsequent user comment (without the marker), the user comment is returned as new feedback while the i2code reply is filtered out
  - Evidence: Unit test provides a thread with [user comment, i2code reply, user follow-up]; asserts both user comments are returned but the i2code reply is filtered out (Scenario 4 from spec)
  - Steps:
    - [ ] Write a failing test simulating Scenario 4: user comment → i2code reply → user follow-up; assert the follow-up is included in results
    - [ ] Verify the existing implementation from Task 1.3 already handles this correctly (the filter is per-comment body, not per-thread)
    - [ ] If the test passes immediately, this validates the design; if not, fix the filtering logic
    - Implement using TDD

## Steel Thread 2: Resolved Conversation Filtering

This thread adds the secondary defense: comments in resolved review threads are skipped. This is US-2.1 and US-2.2, covering Scenarios 3, 5, and 6 from the spec.

- [ ] **Task 2.1: GitHubClient retrieves resolved review thread comment IDs via GraphQL**
  - TaskType: OUTCOME
  - Entrypoint: `pytest`
  - Observable: A new method on `GitHubClient` (e.g., `get_resolved_review_comment_ids`) executes a `gh api graphql` query and returns a `set[int]` of `databaseId` values for comments belonging to resolved review threads
  - Evidence: Unit test mocks the `gh api graphql` subprocess call, provides sample GraphQL response with a mix of resolved and unresolved threads, and asserts only comment IDs from resolved threads are returned
  - Steps:
    - [ ] Read `src/i2code/implement/github_client.py` to understand existing patterns for `gh` CLI invocations
    - [ ] Write a failing test for `get_resolved_review_comment_ids(owner, repo, pr_number)` that mocks the subprocess call and asserts correct ID extraction
    - [ ] Implement the method using `gh api graphql` with the query from the spec (FR-3)
    - [ ] The query uses `first: 100` for both `reviewThreads` and `comments` — no pagination needed (NFR-2)
    - [ ] Verify the test passes
    - Implement using TDD

- [ ] **Task 2.2: Comments in resolved review threads are skipped during feedback processing**
  - TaskType: OUTCOME
  - Entrypoint: `pytest`
  - Observable: During feedback processing, after marker filtering (Task 1.3), comments whose IDs appear in the resolved-thread set are excluded from the returned list and marked as processed in `WorkflowState`
  - Evidence: Unit test mocks `get_resolved_review_comment_ids` to return a set of IDs; provides unprocessed comments including some with those IDs; asserts resolved-thread comments are filtered out and marked processed (Scenario 3 from spec)
  - Steps:
    - [ ] Write a failing test: provide unprocessed review comments, mock `get_resolved_review_comment_ids` to return IDs of some, assert those are excluded and marked processed
    - [ ] Integrate the resolved-thread filter into the processing pipeline after the marker filter (FR-4 ordering: processed IDs → marker → resolved threads → mark filtered as processed)
    - [ ] Verify the test passes
    - Implement using TDD

- [ ] **Task 2.3: Mixed resolved and unresolved threads are handled correctly**
  - TaskType: OUTCOME
  - Entrypoint: `pytest`
  - Observable: Given multiple review threads — some resolved, some not — only comments from unresolved threads (that also pass marker filtering) are returned as new feedback
  - Evidence: Unit test provides comments from 3 threads (A resolved, B unresolved, C resolved), mocks resolved-thread IDs for A and C; asserts only Thread B's comment is returned (Scenario 6 from spec)
  - Steps:
    - [ ] Write a failing test simulating Scenario 6 with three threads
    - [ ] Verify the existing implementation from Task 2.3 handles this correctly
    - [ ] If the test passes immediately, this validates the design; if not, fix the filtering logic
    - Implement using TDD

---

## Steel Thread 3: Integration Test: Real PR Filtering
Verify self-comment marker filtering and resolved-thread filtering against a real GitHub PR. No Claude invocation — this tests the filtering and reply mechanics using actual GitHub API responses.

- [ ] **Task 3.1: Create test repo in GH_TEST_ORG**
  - TaskType: INFRA
  - Entrypoint: `test script`
  - Observable: Test script creates a temporary repo in the GH_TEST_ORG organization, initializes it with a file, and stores the repo name for subsequent tasks. Cleans up the repo at the end of the test run.
  - Evidence: `gh repo view confirms the repo exists in GH_TEST_ORG during the test; repo is deleted in cleanup`
  - Steps:
    - [ ] Create a test script that reads GH_TEST_ORG env var (fail if unset)
    - [ ] Create a temporary repo in GH_TEST_ORG with gh repo create
    - [ ] Push an initial commit with a source file (needed for review comments on a diff)
    - [ ] Register cleanup to delete the repo at script exit
- [ ] **Task 3.2: Create test PR with comments and verify marker-bearing replies are skipped**
  - TaskType: OUTCOME
  - Entrypoint: `test script`
  - Observable: Using the GH_TEST_ORG repo from Task 3.1, creates a PR, posts a review comment, replies with a marker-prefixed comment, then runs the feedback fetching logic and confirms the marker-bearing reply is excluded from unprocessed feedback
  - Evidence: `Test script exits 0; marker-bearing comment is not in the returned feedback list and is marked as processed`
  - Steps:
    - [ ] Create a branch and PR in the GH_TEST_ORG test repo
    - [ ] Post a review comment on the PR
    - [ ] Post a reply with i2code marker prefix to simulate an i2code reply
    - [ ] Invoke the feedback fetching logic and assert the marker reply is filtered out
    - [ ] Clean up: close the PR
- [ ] **Task 3.3: Verify comments in resolved threads are skipped**
  - TaskType: OUTCOME
  - Entrypoint: `test script`
  - Observable: Using the GH_TEST_ORG repo from Task 3.1, creates a PR with review comments in multiple threads, resolves one thread, then runs the feedback fetching logic and confirms comments in the resolved thread are excluded
  - Evidence: `Test script exits 0; comments from the resolved thread are not in the returned feedback list and are marked as processed; comments from unresolved threads are included`
  - Steps:
    - [ ] Create a branch and PR in the GH_TEST_ORG test repo with changes that support multiple review comment threads
    - [ ] Post review comments on different parts of the diff
    - [ ] Resolve one thread using gh api graphql mutation
    - [ ] Invoke the feedback fetching logic and assert resolved-thread comments are filtered out while unresolved-thread comments are returned
    - [ ] Clean up: close the PR
## Change History
### 2026-03-13 16:58 - delete-task
Rate limiting is not a realistic concern (120 req/hr vs 5000 limit). Transient network errors affect REST calls equally. Graceful degradation test adds complexity without meaningful value.

### 2026-03-13 16:58 - replace-task
Simplified from a full task to basic error handling. Network errors are the only realistic failure mode and affect REST calls equally. A single test case within 2.1 tests is sufficient.

### 2026-03-13 16:58 - delete-task
Errors should propagate as exceptions, not be masked with try/except returning empty sets. If GraphQL fails, the caller should know. No silent degradation.

### 2026-03-13 17:01 - insert-thread-after
All existing tasks use mocked unit tests. Need integration tests against real GitHub PRs to verify filtering works with actual API responses.

### 2026-03-13 17:02 - insert-task-before
Integration tests need a real GitHub repo. Using GH_TEST_ORG keeps test repos isolated from production.

### 2026-03-13 17:02 - replace-task
Updated to reference GH_TEST_ORG test repo from Task 3.1

### 2026-03-13 17:02 - replace-task
Updated to reference GH_TEST_ORG test repo from Task 3.1
