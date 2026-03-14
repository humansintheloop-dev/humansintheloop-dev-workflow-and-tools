# Specification: PR Feedback Self-Reply Prevention

## Purpose and Background

The `i2code implement --address-review-comments` feature polls a GitHub PR for new review feedback every 30 seconds, triages it via Claude, and either applies fixes or asks clarifying questions. During real-world usage on [isolarium PR #5](https://github.com/humansintheloop-dev/isolarium/pull/5#discussion_r2921786223), the system entered an infinite reply loop — treating its own replies as new user feedback and responding to them indefinitely.

This happened because `i2code` runs as the user's own GitHub account (there is no dedicated bot account), and the system has no mechanism to distinguish its own replies from human comments.

## Target Users

- Developers using `i2code implement --address-review-comments` to automatically address PR review feedback.

## Problem Statement

The PR feedback processor (`PullRequestReviewProcessor`) fetches all comments and filters only by previously-processed IDs (`WorkflowState.processed_comment_ids`). When the system posts a reply (e.g., "Fixed in abc123" or a clarification question), the next poll cycle picks up that reply as new unprocessed feedback, triages it, and replies again — creating an infinite loop.

A secondary issue: the system processes comments in conversations that the user has already resolved manually, leading to unnecessary re-engagement.

## Goals

1. Eliminate self-reply loops by reliably identifying and skipping i2code-authored comments.
2. Respect conversation resolution — do not process feedback in threads the user has already resolved.
3. Minimize complexity — no thread-level double-reply heuristics or architectural changes.

## In Scope

- Adding an HTML comment marker (`<!-- i2code -->`) to all i2code replies.
- Filtering out marker-bearing comments during feedback processing.
- Querying GitHub for resolved review thread status via `gh api graphql`.
- Skipping comments belonging to resolved review threads.
- Marking skipped comments as processed in `WorkflowState`.

## Out of Scope

- Dedicated GitHub bot account or GitHub App integration.
- Thread-level double-reply detection (marker + processed-ID tracking is sufficient).
- Changes to the triage prompt or Claude invocation.
- Changes to the poll interval or exit conditions in the review loop.
- Filtering resolved conversations for issue/PR-level comments (only review threads have `isResolved`).

## Functional Requirements

### FR-1: Self-comment marker on all replies

Every comment posted by `i2code` must be prefixed with `<!-- i2code -->` as the first line, followed by the reply body. This applies to all reply types:

**Fix replies** (posted by `_push_and_reply` in `pull_request_review_processor.py:277-302`):

Current format:
```
Fixed in abc12345
```

New format:
```
<!-- i2code -->
Fixed in abc12345
```

**Clarification replies** (posted by `_reply_with_clarifications` in `pull_request_review_processor.py:179-200`):

For review comments — current format:
```
Could you please clarify what you mean?
```

New format:
```
<!-- i2code -->
Could you please clarify what you mean?
```

For conversation comments — current format:
```
Re: comment 12345

Could you please clarify what you mean?
```

New format:
```
<!-- i2code -->
Re: comment 12345

Could you please clarify what you mean?
```

The marker insertion should happen at a single point — in the reply body construction, before passing to `GitHubClient.reply_to_review_comment()` or `GitHubClient.reply_to_pr_comment()`. The `GitHubClient` methods remain unchanged (thin wrappers).

### FR-2: Filter out self-comments during processing

In `PullRequestReviewProcessor._get_new_feedback()` (currently at `pull_request_review_processor.py:328-333`), after filtering by processed IDs, additionally filter out any comment whose `body` field starts with `<!-- i2code -->`.

The check must be: `comment.get("body", "").startswith("<!-- i2code -->")`.

Filtered i2code comments must be marked as processed in `WorkflowState` (same as if they had been triaged) so they do not reappear in subsequent poll cycles.

### FR-3: Skip comments in resolved review threads

Add a new method to `GitHubClient` that queries resolved review threads via `gh api graphql`. The GraphQL query should fetch review threads for a given PR and return the set of comment IDs belonging to resolved threads.

The query structure:

```graphql
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          isResolved
          comments(first: 100) {
            nodes {
              databaseId
            }
          }
        }
      }
    }
  }
}
```

The `databaseId` field maps to the REST API `id` field used throughout the existing code.

In the processor, after fetching unprocessed comments, remove any review comment whose ID appears in the resolved-thread set. Mark these as processed in `WorkflowState`.

**Note:** This only applies to review comments (code-level comments that belong to review threads). PR-level conversation comments (`/issues/{pr}/comments`) do not have a resolution concept in GitHub's API and are not affected.

### FR-4: Processing order

Within `_fetch_unprocessed_feedback` (or its equivalent), the filtering order is:

1. Filter by processed IDs (existing behavior).
2. Filter out `<!-- i2code -->` marker comments (FR-2).
3. Filter out comments in resolved review threads (FR-3).
4. Mark all filtered-out comments from steps 2 and 3 as processed.

## Non-Functional Requirements

### NFR-1: No visible change to PR conversation

The `<!-- i2code -->` marker is an HTML comment, invisible when rendered in GitHub's markdown. Existing reply content and formatting remain unchanged from the reader's perspective.

### NFR-2: GraphQL pagination

The GraphQL query uses `first: 100` for both review threads and comments per thread. For PRs with more than 100 review threads or 100 comments in a single thread, pagination is not required — these are extreme edge cases, and missing some resolved threads in those cases is an acceptable degradation (the system would simply process those comments normally rather than skipping them).

### NFR-3: GraphQL failure tolerance

If the `gh api graphql` call fails (network error, permission issue, rate limit), the system should log a warning and proceed without resolved-thread filtering. The self-comment marker (FR-1 + FR-2) is the primary defense against loops; resolved-thread filtering is a secondary optimization.

### NFR-4: Performance

The GraphQL call adds one API request per poll cycle (30 seconds). This is negligible relative to the existing REST calls and Claude invocations.

## Success Metrics

1. **No self-reply loops** — in a PR where i2code replies to a comment, the next poll cycle does not treat that reply as new feedback.
2. **Resolved conversations are skipped** — comments in resolved review threads are not processed or replied to.
3. **Normal feedback flow is unaffected** — legitimate user comments continue to be triaged, fixed, and replied to as before.

## Epics and User Stories

### Epic 1: Self-Comment Identification

**US-1.1:** As i2code, when I post a reply to a PR comment, I prepend `<!-- i2code -->` to the body so that my comments are machine-identifiable.

**US-1.2:** As i2code, when I fetch unprocessed feedback, I skip any comment whose body starts with `<!-- i2code -->` and mark it as processed.

### Epic 2: Resolved Conversation Filtering

**US-2.1:** As i2code, when I fetch unprocessed review comments, I query GitHub's GraphQL API for resolved review threads and skip comments belonging to resolved threads.

**US-2.2:** As i2code, if the GraphQL query fails, I log a warning and continue processing without resolved-thread filtering.

## User-Facing Scenarios

### Scenario 1: Self-reply prevention (primary end-to-end scenario)

1. User leaves a review comment on a PR: "Why is this function public?"
2. i2code polls, picks up the comment, triages it as needing clarification.
3. i2code replies: `<!-- i2code -->\nThis function is public because it's called from the integration test module.`
4. i2code polls again 30 seconds later.
5. The reply is fetched but filtered out because its body starts with `<!-- i2code -->`.
6. The reply's ID is marked as processed in `WorkflowState`.
7. No further replies are posted. The conversation has one user comment and one i2code reply.

### Scenario 2: Fix reply does not trigger loop

1. User leaves a review comment: "This variable name is misleading."
2. i2code triages it as a fix, renames the variable, pushes, and replies: `<!-- i2code -->\nFixed in abc12345`
3. Next poll: the "Fixed in" reply is filtered out by the marker. No loop.

### Scenario 3: Resolved conversation is skipped

1. User leaves a review comment: "Consider using a constant here."
2. Before i2code processes it, the user resolves the conversation on GitHub.
3. i2code polls, fetches the comment, queries GraphQL, sees the thread is resolved.
4. The comment is skipped and marked as processed. No reply is posted.

### Scenario 4: User continues conversation after i2code reply

1. User leaves a comment. i2code replies with a clarification.
2. User replies again with more detail (this is a new comment with a new ID, no `<!-- i2code -->` marker).
3. i2code picks up the user's new reply as fresh feedback, triages and responds normally.

### Scenario 5: GraphQL failure degrades gracefully

1. i2code polls for feedback. The `gh api graphql` call fails (e.g., network timeout).
2. A warning is logged.
3. Feedback processing continues — self-comment marker filtering (FR-2) still prevents loops.
4. The only impact: comments in resolved threads may be processed unnecessarily.

### Scenario 6: Mixed resolved and unresolved threads

1. A PR has three review threads: Thread A (resolved), Thread B (unresolved), Thread C (resolved).
2. Each thread has one unprocessed user comment.
3. i2code fetches all three, queries GraphQL, determines A and C are resolved.
4. Comments from A and C are skipped and marked processed. Only Thread B's comment is triaged.
