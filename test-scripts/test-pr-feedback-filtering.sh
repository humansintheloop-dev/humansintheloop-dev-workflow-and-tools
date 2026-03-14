#!/usr/bin/env bash
# Integration test for PR feedback self-reply filtering and resolved thread filtering.
#
# This script:
# 1. Creates a temporary repo in GH_TEST_ORG
# 2. Pushes an initial commit with a source file (needed for review comments on a diff)
# 3. Runs filtering integration tests (Tasks 3.2, 3.3)
# 4. Cleans up the repo on exit
#
# Environment:
#   GH_TEST_ORG  GitHub organization for repo creation (required)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# --- Configuration ---

if [ -z "${GH_TEST_ORG:-}" ]; then
    log_error "GH_TEST_ORG environment variable is not set"
    exit 1
fi

REPO_NAME="test-pr-feedback-$$-$(date +%s)"
REPO_FULL_NAME="$GH_TEST_ORG/$REPO_NAME"
CLONE_DIR=""

# --- Cleanup ---

cleanup() {
    local exit_code=$?

    if [ -n "$REPO_FULL_NAME" ]; then
        log_info "Deleting GitHub repository: $REPO_FULL_NAME"
        gh repo delete "$REPO_FULL_NAME" --yes 2>/dev/null || true
    fi

    if [ -n "$CLONE_DIR" ] && [ -d "$CLONE_DIR" ]; then
        log_info "Removing temp directory: $CLONE_DIR"
        rm -rf "$CLONE_DIR"
    fi

    exit $exit_code
}

trap cleanup EXIT

# --- Create repo with initial commit ---

log_info "Creating temporary repo: $REPO_FULL_NAME"

CLONE_DIR="$(mktemp -d)"

cd "$CLONE_DIR"
git init -b main
git config user.email "test@test.com"
git config user.name "Test"

cat > hello.py <<'PYEOF'
def greet(name):
    return f"Hello, {name}!"


def farewell(name):
    return f"Goodbye, {name}!"
PYEOF

git add hello.py
git commit -m "Initial commit with source file"

gh repo create "$REPO_FULL_NAME" --private --source . --push

log_success "Repo created and initial commit pushed"

# --- Verify repo exists ---

gh repo view "$REPO_FULL_NAME" --json name > /dev/null
log_success "Verified repo exists: $REPO_FULL_NAME"

echo ""
echo "=== PR Feedback Filtering Integration Test ==="
echo "  Repo: $REPO_FULL_NAME"
echo "  Clone: $CLONE_DIR"
echo ""
log_success "Infrastructure ready (Task 3.1 complete)"

# =====================================================
# Task 3.2: Marker-bearing replies are skipped
# =====================================================

echo ""
echo "--- Task 3.2: Marker-bearing replies are skipped ---"

# Step 1: Create a branch and PR
log_info "Creating branch and PR"

git checkout -b test-marker-filtering

cat > feature.py <<'PYEOF'
def new_feature():
    return "implemented"
PYEOF

git add feature.py
git commit -m "Add feature file"
git push -u origin test-marker-filtering

PR_URL=$(gh pr create --repo "$REPO_FULL_NAME" --title "Test marker filtering" --body "Task 3.2 test" --base main)
PR_NUMBER=$(echo "$PR_URL" | grep -oE '[0-9]+$')
log_success "Created PR #$PR_NUMBER"

# Step 2: Post a review comment on the PR
log_info "Posting review comment"

COMMIT_SHA=$(git rev-parse HEAD)
REVIEW_COMMENT_JSON=$(gh api "repos/$REPO_FULL_NAME/pulls/$PR_NUMBER/comments" \
    -f body="Please refactor this function" \
    -f commit_id="$COMMIT_SHA" \
    -f path="feature.py" \
    -F line=1 \
    -f side="RIGHT")
COMMENT_ID=$(echo "$REVIEW_COMMENT_JSON" | jq -r '.id')
log_success "Posted review comment (id=$COMMENT_ID)"

# Step 3: Post a reply with i2code marker prefix
log_info "Posting i2code marker reply"

MARKER_BODY="<!-- i2code -->
Fixed in abc1234"
gh api "repos/$REPO_FULL_NAME/pulls/$PR_NUMBER/comments/$COMMENT_ID/replies" \
    -f body="$MARKER_BODY" > /dev/null
log_success "Posted marker-bearing reply"

# Step 4: Fetch comments and verify marker reply is filtered out
log_info "Verifying marker-bearing reply is filtered by _filter_self_comments"

cd "$PROJECT_ROOT"
REPO_FULL_NAME="$REPO_FULL_NAME" PR_NUMBER="$PR_NUMBER" \
    uv run --python 3.12 python3 -c "
import os, subprocess, json, sys

repo = os.environ['REPO_FULL_NAME']
pr = os.environ['PR_NUMBER']

# Fetch all review comments from the real GitHub API
result = subprocess.run(
    ['gh', 'api', f'repos/{repo}/pulls/{pr}/comments', '--jq', '.'],
    capture_output=True, text=True,
)
assert result.returncode == 0, f'gh api failed: {result.stderr}'
comments = json.loads(result.stdout)

print(f'  Fetched {len(comments)} review comments')
assert len(comments) == 2, f'Expected 2 comments (original + reply), got {len(comments)}'

# Run the actual filtering logic
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

user_comments, self_comment_ids = PullRequestReviewProcessor._filter_self_comments(comments)

print(f'  User comments: {len(user_comments)}')
print(f'  Self (marker) comment IDs: {self_comment_ids}')

assert len(user_comments) == 1, f'Expected 1 user comment, got {len(user_comments)}'
assert len(self_comment_ids) == 1, f'Expected 1 self comment ID, got {len(self_comment_ids)}'
assert 'Please refactor' in user_comments[0]['body'], (
    f'User comment body mismatch: {user_comments[0][\"body\"]}'
)

# Verify the filtered comment is the marker-bearing one
marker_id = self_comment_ids[0]
marker_comment = [c for c in comments if c['id'] == marker_id][0]
assert marker_comment['body'].startswith('<!-- i2code -->'), (
    f'Filtered comment does not start with marker: {marker_comment[\"body\"][:50]}'
)

print('  PASS: marker-bearing reply correctly excluded from unprocessed feedback')
print('  PASS: marker comment ID would be marked as processed')
"
cd "$CLONE_DIR"
log_success "Task 3.2 passed: marker-bearing replies are skipped"

# Step 5: Clean up PR (repo deletion in cleanup trap handles full cleanup)
log_info "Closing PR #$PR_NUMBER"
gh pr close "$PR_NUMBER" --repo "$REPO_FULL_NAME" > /dev/null
log_success "PR #$PR_NUMBER closed"

# =====================================================
# Task 3.3: Comments in resolved threads are skipped
# =====================================================

echo ""
echo "--- Task 3.3: Comments in resolved threads are skipped ---"

# Step 1: Create a branch with changes that support multiple review comment threads
log_info "Creating branch and PR for resolved-thread test"

git checkout main
git checkout -b test-resolved-threads

cat > utils.py <<'PYEOF'
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b
PYEOF

git add utils.py
git commit -m "Add utils module with multiple functions"
git push -u origin test-resolved-threads

PR3_URL=$(gh pr create --repo "$REPO_FULL_NAME" --title "Test resolved thread filtering" --body "Task 3.3 test" --base main)
PR3_NUMBER=$(echo "$PR3_URL" | grep -oE '[0-9]+$')
log_success "Created PR #$PR3_NUMBER"

# Step 2: Post review comments on different parts of the diff (different lines)
log_info "Posting review comments on different lines"

COMMIT_SHA=$(git rev-parse HEAD)

COMMENT_A_JSON=$(gh api "repos/$REPO_FULL_NAME/pulls/$PR3_NUMBER/comments" \
    -f body="Thread A: Please rename this function" \
    -f commit_id="$COMMIT_SHA" \
    -f path="utils.py" \
    -F line=1 \
    -f side="RIGHT")
COMMENT_A_ID=$(echo "$COMMENT_A_JSON" | jq -r '.id')
log_success "Posted thread A comment on line 1 (id=$COMMENT_A_ID)"

COMMENT_B_JSON=$(gh api "repos/$REPO_FULL_NAME/pulls/$PR3_NUMBER/comments" \
    -f body="Thread B: Add type hints here" \
    -f commit_id="$COMMIT_SHA" \
    -f path="utils.py" \
    -F line=5 \
    -f side="RIGHT")
COMMENT_B_ID=$(echo "$COMMENT_B_JSON" | jq -r '.id')
log_success "Posted thread B comment on line 5 (id=$COMMENT_B_ID)"

# Step 3: Resolve thread A using gh api graphql mutation
log_info "Resolving thread A via GraphQL"

# First, find the thread node ID for the thread containing comment A
# shellcheck disable=SC2016
THREAD_A_NODE_ID=$(gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100) {
        nodes {
          id
          comments(first: 100) {
            nodes {
              databaseId
            }
          }
        }
      }
    }
  }
}' -F "owner=$GH_TEST_ORG" -F "repo=$REPO_NAME" -F "pr=$PR3_NUMBER" \
    --jq ".data.repository.pullRequest.reviewThreads.nodes[] | select(.comments.nodes[].databaseId == $COMMENT_A_ID) | .id")

if [ -z "$THREAD_A_NODE_ID" ]; then
    log_error "Could not find thread node ID for comment A ($COMMENT_A_ID)"
    exit 1
fi
log_success "Found thread A node ID: $THREAD_A_NODE_ID"

# shellcheck disable=SC2016
gh api graphql -f query='
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread {
      isResolved
    }
  }
}' -f "threadId=$THREAD_A_NODE_ID" > /dev/null
log_success "Resolved thread A"

# Step 4: Invoke feedback fetching logic and verify resolved-thread comments are filtered
log_info "Verifying resolved-thread comments are filtered by _filter_resolved_thread_comments"

cd "$PROJECT_ROOT"
REPO_FULL_NAME="$REPO_FULL_NAME" PR_NUMBER="$PR3_NUMBER" \
    COMMENT_A_ID="$COMMENT_A_ID" COMMENT_B_ID="$COMMENT_B_ID" \
    uv run --python 3.12 python3 -c "
import os, subprocess, json, sys

repo = os.environ['REPO_FULL_NAME']
pr = int(os.environ['PR_NUMBER'])
comment_a_id = int(os.environ['COMMENT_A_ID'])
comment_b_id = int(os.environ['COMMENT_B_ID'])
owner, repo_name = repo.split('/')

# Fetch all review comments from the real GitHub API
result = subprocess.run(
    ['gh', 'api', f'repos/{repo}/pulls/{pr}/comments', '--jq', '.'],
    capture_output=True, text=True,
)
assert result.returncode == 0, f'gh api failed: {result.stderr}'
comments = json.loads(result.stdout)

print(f'  Fetched {len(comments)} review comments')
assert len(comments) == 2, f'Expected 2 comments, got {len(comments)}'

# Verify get_resolved_review_comment_ids returns comment A's ID
from i2code.implement.github_client import GitHubClient
gh_client = GitHubClient()
resolved_ids = gh_client.get_resolved_review_comment_ids(owner, repo_name, pr)

print(f'  Resolved comment IDs: {resolved_ids}')
assert comment_a_id in resolved_ids, (
    f'Comment A (id={comment_a_id}) should be in resolved set, got {resolved_ids}'
)
assert comment_b_id not in resolved_ids, (
    f'Comment B (id={comment_b_id}) should NOT be in resolved set, got {resolved_ids}'
)

# Call the production filtering method
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

remaining, filtered_ids = PullRequestReviewProcessor._exclude_resolved_comments(comments, resolved_ids)

print(f'  Remaining (unresolved) comments: {len(remaining)}')
print(f'  Filtered (resolved) comment IDs: {filtered_ids}')

assert len(remaining) == 1, f'Expected 1 remaining comment, got {len(remaining)}'
assert remaining[0]['id'] == comment_b_id, (
    f'Remaining comment should be B (id={comment_b_id}), got id={remaining[0][\"id\"]}'
)
assert 'Thread B' in remaining[0]['body'], (
    f'Remaining comment body mismatch: {remaining[0][\"body\"]}'
)
assert len(filtered_ids) == 1, f'Expected 1 filtered ID, got {len(filtered_ids)}'
assert filtered_ids[0] == comment_a_id, (
    f'Filtered ID should be A (id={comment_a_id}), got {filtered_ids[0]}'
)

print('  PASS: resolved-thread comments correctly excluded from feedback')
print('  PASS: resolved comment IDs would be marked as processed')
print('  PASS: unresolved-thread comments correctly included in feedback')
"
cd "$CLONE_DIR"
log_success "Task 3.3 passed: comments in resolved threads are skipped"

# Step 5: Clean up PR
log_info "Closing PR #$PR3_NUMBER"
gh pr close "$PR3_NUMBER" --repo "$REPO_FULL_NAME" > /dev/null
log_success "PR #$PR3_NUMBER closed"
