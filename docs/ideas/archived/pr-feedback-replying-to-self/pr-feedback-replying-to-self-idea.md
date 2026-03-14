# PR Feedback: Prevent Self-Reply Loop

## Problem

The `i2code implement --address-review-comments` PR feedback processing mechanism gets stuck in an infinite loop replying to its own comments.

**Observed in:** [isolarium PR #5](https://github.com/humansintheloop-dev/isolarium/pull/5#discussion_r2921786223)

**Reproduction:**
1. User asks a question (e.g., "Why?")
2. i2code replies with a useful answer
3. i2code treats its own answer as new feedback, replies to that, and so on
4. Loop continued until the conversation was resolved manually

**Root cause:** The system has no mechanism to distinguish its own replies from user comments. It runs as the user's GitHub account (no dedicated bot account), so author-based filtering is not viable.

## Solution

### 1. Self-comment identification via HTML comment marker

- Prefix **all** i2code replies (fixes, clarifications, any future types) with `<!-- i2code -->` on the first line
- When processing comments, filter out any comment whose body starts with `<!-- i2code -->`
- Mark filtered i2code comments as processed in `WorkflowState` to avoid redundant filtering on subsequent poll cycles
- Filter in `pull_request_review_processor.py` (processor layer), not in `github_client.py` (client stays a thin API wrapper)

### 2. Skip resolved conversations

- Use `gh api graphql` to query `isResolved` on review threads
- Skip unprocessed comments belonging to resolved conversations — if the user resolved it themselves, i2code should not re-engage

### 3. Keep it simple

- No thread-level double-reply checks — the marker filtering plus processed-ID tracking is sufficient to prevent loops
- No additional complexity beyond the two mechanisms above
