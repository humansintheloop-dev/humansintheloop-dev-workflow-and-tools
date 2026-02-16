#!/usr/bin/env bash
# HELP_START
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
#   --worktree DIR    Resume execution in a previously created worktree directory
#   --non-interactive Run Claude in non-interactive mode (uses -p flag)
#   --plan-file FILE  Alternative plan file to use (renamed to -plan.md in repo)
#   --extra-prompt TEXT  Extra text to append to Claude's prompt
#   --idea DIR        Alternative idea directory to use (default: tests/kafka-security-poc)
#   --isolate         Run inside an isolarium VM (uses i2code implement --isolate)
#   -h, --help        Show this help message
# HELP_END

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration paths
CONFIG_FILES_DIR="$PROJECT_ROOT/config-files"
TEST_IDEA_SOURCE="$PROJECT_ROOT/test-ideas/kafka-security-poc"
WORKTREE_SCRIPT="$PROJECT_ROOT/workflow-scripts/implement-with-worktree.sh"

# Test configuration
TEST_REPO_PREFIX="test-wt-e2e"
CLEANUP_ON_EXIT=true
DRY_RUN=false
SETUP_ONLY=false
WORKTREE_DIR=""
NON_INTERACTIVE=false
PLAN_FILE=""
EXTRA_PROMPT=""
IDEA_DIR=""
ISOLATE=false

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
    # Extract help text between HELP_START and HELP_END markers
    sed -n '/^# HELP_START$/,/^# HELP_END$/p' "$0" | sed '1d;$d' | sed 's/^# //' | sed 's/^#//'
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
            --worktree)
                WORKTREE_DIR="$2"
                CLEANUP_ON_EXIT=false
                shift 2
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --plan-file)
                PLAN_FILE="$2"
                shift 2
                ;;
            --extra-prompt)
                EXTRA_PROMPT="$2"
                shift 2
                ;;
            --idea)
                if [ ! -d "$2" ]; then
                    log_error "Idea directory not found: $2"
                    exit 1
                fi
                # Convert to absolute path so it works after cd
                IDEA_DIR="$(cd "$2" && pwd)"
                shift 2
                ;;
            --isolate)
                ISOLATE=true
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

    local idea_source
    idea_source="$(get_idea_source)"
    if [ ! -d "$idea_source" ]; then
        log_error "Test idea directory not found at $idea_source"
        exit 1
    fi

    if [ "$ISOLATE" != true ] && [ ! -x "$WORKTREE_SCRIPT" ]; then
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
    'Bash(git commit:*)',
    'Bash(git check-ignore:*)',
    'Bash(mkdir -p:*)',
    'Bash(./test-scripts/test-*.sh)',
    'Bash(docker compose config:*)',
    'Write',
    'Edit'
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

get_idea_source() {
    if [ -n "$IDEA_DIR" ]; then
        echo "$IDEA_DIR"
    else
        echo "$TEST_IDEA_SOURCE"
    fi
}

get_idea_name() {
    basename "$(get_idea_source)"
}

copy_test_idea() {
    log_info "Copying test idea directory..."

    local idea_source
    local idea_name
    idea_source="$(get_idea_source)"
    idea_name="$(get_idea_name)"

    mkdir -p "$TEMP_DIR/docs/features/$idea_name"

    # If alternative plan file is specified, exclude both the original and alternative plan files
    # (the alternative will be copied separately with the correct name)
    if [ -n "$PLAN_FILE" ]; then
        local original_plan="${idea_name}-plan.md"
        for file in "$idea_source"/*; do
            local filename
            filename=$(basename "$file")
            if [ "$filename" = "$original_plan" ]; then
                log_info "  Skipping original plan file: $original_plan"
            elif [ "$filename" = "$PLAN_FILE" ]; then
                log_info "  Skipping alternative plan file: $PLAN_FILE (will be renamed)"
            else
                cp -r "$file" "$TEMP_DIR/docs/features/$idea_name/"
            fi
        done
    else
        cp -r "$idea_source"/* "$TEMP_DIR/docs/features/$idea_name/"
    fi

    log_success "Test idea directory copied: docs/features/$idea_name"
}

copy_plan_file() {
    if [ -z "$PLAN_FILE" ]; then
        return
    fi

    log_info "Copying alternative plan file..."

    local idea_source
    local idea_name
    idea_source="$(get_idea_source)"
    idea_name="$(get_idea_name)"

    local source_plan="$idea_source/$PLAN_FILE"
    local dest_dir="$TEMP_DIR/docs/features/$idea_name"
    local dest_plan="$dest_dir/${idea_name}-plan.md"

    if [ ! -f "$source_plan" ]; then
        log_error "Plan file not found: $source_plan"
        exit 1
    fi

    cp "$source_plan" "$dest_plan"
    log_success "Plan file copied: $PLAN_FILE -> ${idea_name}-plan.md"
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

    local idea_name
    idea_name="$(get_idea_name)"

    # Build command with optional flags
    local cmd
    if [ "$ISOLATE" = true ]; then
        cmd=("i2code" "implement" "--isolate")
    else
        cmd=("$WORKTREE_SCRIPT")
    fi
    if [ "$NON_INTERACTIVE" = true ]; then
        cmd+=("--non-interactive")
    fi
    if [ -n "$EXTRA_PROMPT" ]; then
        cmd+=("--extra-prompt" "$EXTRA_PROMPT")
    fi
    cmd+=("$TEMP_DIR/docs/features/$idea_name")

    "${cmd[@]}"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "implement-with-worktree.sh completed successfully"
    else
        log_error "implement-with-worktree.sh failed with exit code $exit_code"
        exit $exit_code
    fi
}

resume_from_worktree() {
    log_info "Resuming from worktree: $WORKTREE_DIR"

    if [ ! -d "$WORKTREE_DIR" ]; then
        log_error "Worktree directory not found: $WORKTREE_DIR"
        exit 1
    fi

    # Derive the main repo directory from the worktree path
    # Worktree format: <repo-dir>-wt-<idea-name>
    # We need to find the main repo by removing the -wt-* suffix
    local worktree_basename
    worktree_basename=$(basename "$WORKTREE_DIR")

    # Extract the base repo name (everything before the last -wt-)
    local repo_basename
    repo_basename="${worktree_basename%-wt-*}"

    TEMP_DIR="$(dirname "$WORKTREE_DIR")/$repo_basename"

    if [ ! -d "$TEMP_DIR" ]; then
        log_error "Main repo directory not found: $TEMP_DIR"
        exit 1
    fi

    log_info "Main repo directory: $TEMP_DIR"

    # Get GitHub repo name from git remote
    cd "$TEMP_DIR"
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$remote_url" ]; then
        # Extract owner/repo from URL
        GITHUB_REPO_FULL_NAME=$(echo "$remote_url" | sed -E 's|.*github.com[:/]([^/]+/[^/.]+).*|\1|')
        log_info "GitHub repository: $GITHUB_REPO_FULL_NAME"
    fi

    log_success "Resume context loaded"
}

verify_results() {
    log_info "Verifying results..."

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
        local idea_source idea_name
        idea_source="$(get_idea_source)"
        idea_name="$(get_idea_name)"
        echo "Would execute:"
        echo "  1. Create temporary directory"
        echo "  2. Initialize git repository"
        echo "  3. Copy CLAUDE.md to repo root"
        echo "  4. Copy settings.local.json to .claude/"
        echo "  5. Add 'git commit' permission to settings"
        echo "  6. Copy $idea_source to docs/features/$idea_name"
        if [ -n "$PLAN_FILE" ]; then
        echo "  6b. Copy $PLAN_FILE as ${idea_name}-plan.md"
        fi
        echo "  7. Commit all files"
        echo "  8. Create GitHub repository"
        echo "  9. Run implement-with-worktree.sh"
        if [ -n "$EXTRA_PROMPT" ]; then
        echo "      with extra prompt: $EXTRA_PROMPT"
        fi
        echo "  10. Verify results"
        echo ""
        exit 0
    fi

    # Resume from existing worktree if specified
    if [ -n "$WORKTREE_DIR" ]; then
        resume_from_worktree
        run_implement_with_worktree
        verify_results
        echo ""
        log_success "E2E test completed successfully!"
        echo ""
        exit 0
    fi

    check_prerequisites
    create_temp_directory
    initialize_git_repo
    copy_config_files
    copy_test_idea
    copy_plan_file
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
