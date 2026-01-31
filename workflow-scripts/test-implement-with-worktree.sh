#!/usr/bin/env bash
# End-to-end test script for implement-with-worktree.sh
#
# This script:
# 1. Creates a temporary directory for the test
# 2. Initializes a git repo
# 3. Copies config files (CLAUDE.md, settings.local.json)
# 4. Copies test idea directory (kafka-security-poc)
# 5. Commits all files
# 6. Creates a GitHub repository
# 7. Runs implement-with-worktree.sh with real Claude Code
# 8. Verifies tasks are executed successfully
#
# Usage: test-implement-with-worktree.sh [options]
#
# Options:
#   --dry-run         Show what would be done without executing
#   --keep-repo       Don't delete the GitHub repo on exit (for debugging)
#   --setup-only      Only create repo and push, don't run implement-with-worktree
#   -h, --help        Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration paths
CONFIG_FILES_DIR="$PROJECT_ROOT/config-files"
TEST_IDEA_SOURCE="$PROJECT_ROOT/tests/kafka-security-poc"
WORKTREE_SCRIPT="$SCRIPT_DIR/implement-with-worktree.sh"

# Test configuration
TEST_REPO_PREFIX="test-wt-e2e"
CLEANUP_ON_EXIT=true
DRY_RUN=false
SETUP_ONLY=false

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup tracking
GITHUB_REPO_FULL_NAME=""
TEMP_DIR=""

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

show_help() {
    # Extract help text from script header (lines 2-20)
    sed -n '2,20p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

cleanup() {
    local exit_code=$?

    if [ "$CLEANUP_ON_EXIT" = true ]; then
        if [ -n "$GITHUB_REPO_FULL_NAME" ]; then
            log_info "Deleting GitHub repository: $GITHUB_REPO_FULL_NAME"
            gh repo delete "$GITHUB_REPO_FULL_NAME" --yes 2>/dev/null || true
        fi

        if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
            log_info "Removing temporary directory: $TEMP_DIR"
            rm -rf "$TEMP_DIR"
        fi

        # Also clean up any worktree that was created
        local repo_name
        if [ -n "$TEMP_DIR" ]; then
            repo_name=$(basename "$TEMP_DIR")
            local worktree_dir="$(dirname "$TEMP_DIR")/${repo_name}-wt-kafka-security-poc"
            if [ -d "$worktree_dir" ]; then
                log_info "Removing worktree directory: $worktree_dir"
                rm -rf "$worktree_dir"
            fi
        fi
    else
        if [ -n "$GITHUB_REPO_FULL_NAME" ]; then
            log_warning "Keeping GitHub repository: $GITHUB_REPO_FULL_NAME"
        fi
        if [ -n "$TEMP_DIR" ]; then
            log_warning "Keeping temporary directory: $TEMP_DIR"
        fi
    fi

    exit $exit_code
}

trap cleanup EXIT

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --keep-repo)
                CLEANUP_ON_EXIT=false
                shift
                ;;
            --setup-only)
                SETUP_ONLY=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check gh CLI is installed and authenticated
    if ! command -v gh &> /dev/null; then
        log_error "gh CLI is not installed. Install it from https://cli.github.com/"
        exit 1
    fi

    if ! gh auth status &> /dev/null; then
        log_error "gh CLI is not authenticated. Run 'gh auth login' first."
        exit 1
    fi

    # Check required files exist
    if [ ! -f "$CONFIG_FILES_DIR/CLAUDE.md" ]; then
        log_error "CLAUDE.md not found at $CONFIG_FILES_DIR/CLAUDE.md"
        exit 1
    fi

    if [ ! -f "$CONFIG_FILES_DIR/settings.local.json" ]; then
        log_error "settings.local.json not found at $CONFIG_FILES_DIR/settings.local.json"
        exit 1
    fi

    if [ ! -d "$TEST_IDEA_SOURCE" ]; then
        log_error "Test idea directory not found at $TEST_IDEA_SOURCE"
        exit 1
    fi

    if [ ! -x "$WORKTREE_SCRIPT" ]; then
        log_error "implement-with-worktree.sh not found or not executable at $WORKTREE_SCRIPT"
        exit 1
    fi

    log_success "All prerequisites satisfied"
}

get_github_username() {
    gh api user --jq '.login'
}

create_temp_directory() {
    log_info "Creating temporary directory..."

    local unique_id
    unique_id=$(date +%Y%m%d%H%M%S)-$$

    TEMP_DIR=$(mktemp -d -t "${TEST_REPO_PREFIX}-${unique_id}.XXXXXX")
    log_success "Created temporary directory: $TEMP_DIR"
}

initialize_git_repo() {
    log_info "Initializing git repository..."

    cd "$TEMP_DIR"
    git init
    git config user.email "test@test.com"
    git config user.name "Test User"

    log_success "Git repository initialized"
}

copy_config_files() {
    log_info "Copying config files..."

    # Copy CLAUDE.md to repo root
    cp "$CONFIG_FILES_DIR/CLAUDE.md" "$TEMP_DIR/CLAUDE.md"
    log_info "  Copied CLAUDE.md"

    # Create .claude directory and copy settings.local.json
    mkdir -p "$TEMP_DIR/.claude"

    # Copy and modify settings.local.json to add "git commit" permission
    local settings_file="$TEMP_DIR/.claude/settings.local.json"
    cp "$CONFIG_FILES_DIR/settings.local.json" "$settings_file"

    # Add "Bash(git commit:*)" to the allow list if not already present
    # Use Python for reliable JSON manipulation
    python3 -c "
import json
import sys

with open('$settings_file', 'r') as f:
    config = json.load(f)

allow_list = config.get('permissions', {}).get('allow', [])

# Permissions needed for the test
needed_permissions = [
    'Bash(git commit:*)'
]

for perm in needed_permissions:
    if perm not in allow_list:
        allow_list.append(perm)

config.setdefault('permissions', {})['allow'] = allow_list

with open('$settings_file', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"

    log_info "  Copied and updated settings.local.json with git commit permission"

    log_success "Config files copied"
}

copy_test_idea() {
    log_info "Copying test idea directory..."

    mkdir -p "$TEMP_DIR/docs/features"
    cp -r "$TEST_IDEA_SOURCE" "$TEMP_DIR/docs/features/kafka-security-poc"

    log_success "Test idea directory copied: docs/features/kafka-security-poc"
}

commit_all_files() {
    log_info "Committing all files..."

    cd "$TEMP_DIR"
    git add -A
    git commit -m "Initial commit with test idea and config files"

    log_success "Files committed"
}

create_github_repo() {
    log_info "Creating GitHub repository..."

    local repo_name
    local unique_id
    unique_id=$(date +%Y%m%d%H%M%S)-$$
    repo_name="${TEST_REPO_PREFIX}-${unique_id}"

    cd "$TEMP_DIR"

    # Create the GitHub repo from the current directory
    if ! gh repo create "$repo_name" --private --source . --push; then
        log_error "Failed to create GitHub repository"
        exit 1
    fi

    # Get the full repo name
    local username
    username=$(get_github_username)
    GITHUB_REPO_FULL_NAME="${username}/${repo_name}"

    log_success "GitHub repository created: $GITHUB_REPO_FULL_NAME"
}

run_implement_with_worktree() {
    log_info "Running implement-with-worktree.sh..."

    cd "$TEMP_DIR"

    # Run the script with the test idea directory
    # Use --non-interactive so Claude runs with -p flag (no user interaction)
    "$WORKTREE_SCRIPT" --non-interactive "$TEMP_DIR/docs/features/kafka-security-poc"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "implement-with-worktree.sh completed successfully"
    else
        log_error "implement-with-worktree.sh failed with exit code $exit_code"
        exit $exit_code
    fi
}

verify_results() {
    log_info "Verifying results..."

    # Check that commits were made
    cd "$TEMP_DIR"

    local commit_count
    commit_count=$(git rev-list --count HEAD)

    if [ "$commit_count" -gt 1 ]; then
        log_success "Commits created: $commit_count total"
    else
        log_warning "No additional commits created (only initial commit)"
    fi

    # Check PR exists
    if [ -n "$GITHUB_REPO_FULL_NAME" ]; then
        local pr_count
        pr_count=$(gh pr list --repo "$GITHUB_REPO_FULL_NAME" --json number --jq 'length')

        if [ "$pr_count" -gt 0 ]; then
            log_success "Pull requests created: $pr_count"
        else
            log_warning "No pull requests found"
        fi
    fi

    log_success "Verification complete"
}

main() {
    parse_args "$@"

    echo ""
    echo "========================================="
    echo "  implement-with-worktree.sh E2E Test"
    echo "========================================="
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - Commands will not be executed"
        echo ""
        echo "Would execute:"
        echo "  1. Create temporary directory"
        echo "  2. Initialize git repository"
        echo "  3. Copy CLAUDE.md to repo root"
        echo "  4. Copy settings.local.json to .claude/"
        echo "  5. Add 'git commit' permission to settings"
        echo "  6. Copy tests/kafka-security-poc to docs/features/"
        echo "  7. Commit all files"
        echo "  8. Create GitHub repository"
        echo "  9. Run implement-with-worktree.sh"
        echo "  10. Verify results"
        echo ""
        exit 0
    fi

    check_prerequisites
    create_temp_directory
    initialize_git_repo
    copy_config_files
    copy_test_idea
    commit_all_files
    create_github_repo

    if [ "$SETUP_ONLY" = true ]; then
        log_warning "SETUP ONLY - Skipping implement-with-worktree.sh execution"
        log_info "Temporary directory: $TEMP_DIR"
        log_info "GitHub repository: $GITHUB_REPO_FULL_NAME"
        log_info "To run manually:"
        echo ""
        echo "  cd $TEMP_DIR"
        echo "  $WORKTREE_SCRIPT docs/features/kafka-security-poc"
        echo ""

        # Don't cleanup in setup-only mode
        CLEANUP_ON_EXIT=false
        exit 0
    fi

    run_implement_with_worktree
    verify_results

    echo ""
    log_success "E2E test completed successfully!"
    echo ""
}

main "$@"
