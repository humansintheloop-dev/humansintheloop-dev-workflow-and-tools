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
