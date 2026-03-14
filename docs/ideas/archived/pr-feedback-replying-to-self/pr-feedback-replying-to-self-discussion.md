# Discussion: PR Feedback Replying to Self

## Context

The `i2code implement --address-review-comments` feature polls for PR feedback and replies. During real usage on [isolarium PR #5](https://github.com/humansintheloop-dev/isolarium/pull/5#discussion_r2921786223), it entered an infinite reply loop — replying to its own comments as if they were new user feedback.

### Root Cause Analysis (from code exploration)

The current system in `pull_request_review_processor.py`:
- Fetches all PR comments (review, reviews, conversation) via `github_client.py:84-109`
- Filters only by `processed_comment_ids` in `WorkflowState` — no author-based filtering
- Posts replies with no distinguishing prefix (e.g., "Fixed in {sha}" or "Re: comment {id}\n\n{question}")
- Does not check conversation resolution state
- The 30-second poll loop (`worktree_mode.py:88-102`) picks up the system's own replies as new feedback

### Proposed Solution (from idea file)

1. Prefix replies with "i2code says" for identification
2. Filter out comments starting with "i2code says" during processing
3. Skip resolved conversations

---

## Questions & Answers

### Q1: Self-identification strategy — text prefix vs author-based filtering?

Options presented:
- A. Text prefix ("i2code says")
- B. Author-based filtering (skip comments where `user.login` matches the bot account)
- C. Both

**Answer:** i2code doesn't have its own GitHub account — it runs as the user's account. Author-based filtering would suppress the user's own legitimate comments. **Text prefix is the correct approach.**

---

### Q2: Prefix format?

Options presented:
- A. Inline prefix — `"i2code says: Fixed in abc123"`
- B. HTML comment marker — `"<!-- i2code -->\nFixed in abc123"` (invisible, machine-parseable)
- C. Bold markdown prefix — `"**i2code:** Fixed in abc123"` (visible + greppable)

**Answer:** Go with option B — HTML comment marker `"<!-- i2code -->"` on the first line, invisible to readers but machine-parseable. Example:

```
<!-- i2code -->
Fixed in abc123
```

---

### Q3: Should i2code process comments in resolved conversations?

Options presented:
- A. Skip unprocessed comments in resolved conversations
- B. Process all comments regardless of resolution
- C. Skip resolved, but still apply fixes silently

**Answer:** A — skip unprocessed comments in resolved conversations. If the user resolved it themselves, i2code should not re-engage.

---

### Q4: Where should the marker-based filter live?

Options presented:
- A. At fetch time in `github_client.py`
- B. At processing time in `pull_request_review_processor.py` (`_get_new_feedback`)

**Answer:** B — filter in the processor, consistent with current design where `github_client.py` is a thin API wrapper and all filtering logic lives in the processor.

---

### Q5: How should i2code detect resolved conversations?

Options presented:
- A. GraphQL API — direct GraphQL calls, reliable `isResolved` access, but new API style
- B. REST-only heuristic — stay with REST, infer resolution from available fields, less reliable
- C. `gh api graphql` — use `gh` CLI's built-in GraphQL support, same tooling, direct `isResolved` access

**Answer:** C — use `gh api graphql` to access `isResolved` on review threads. Keeps the same `gh` CLI tooling while getting reliable resolution detection.

---

### Q6: Should skipped i2code comments be marked as processed in WorkflowState?

Options presented:
- A. Yes, mark processed — prevents redundant filtering on every poll cycle
- B. No, filter every time — simpler state, but re-filters same comments each cycle

**Answer:** A — mark skipped i2code comments as processed so they don't reappear in unprocessed lists.

---

### Q7: What if i2code is about to reply to a thread where the last comment is already its own?

Options presented:
- A. Never reply twice — skip entirely if last comment in thread is from i2code
- B. Reply if new user comment — skip only if immediate previous comment is from i2code
- C. Always reply once — marker + processed-ID tracking is sufficient, no thread-level checks

**Answer:** C — keep it simple. The `<!-- i2code -->` marker filtering plus processed-ID tracking is sufficient to prevent loops. No additional thread-level checks needed.

---

### Q8: Should the `<!-- i2code -->` marker be applied to all reply types?

Options presented:
- A. All replies — every comment i2code posts gets the marker, consistent and future-proof
- B. Only clarifications — fix replies are short and unlikely to trigger re-processing

**Answer:** A — all replies get the marker. Simple, consistent, future-proof.

---

## Classification

**Type: A — User-facing feature (bug fix)**

**Rationale:** This is a bug fix to an existing user-facing feature (`--address-review-comments`). It directly affects the user's experience on GitHub PRs — the infinite reply loop creates noise and requires manual intervention. The fix involves two concrete changes to the existing processing pipeline (marker-based filtering and resolved conversation detection) with no architectural exploration or infrastructure changes needed.

