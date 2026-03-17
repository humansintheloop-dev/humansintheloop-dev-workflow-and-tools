#!/usr/bin/env bash
# HELP_START
# End-to-end test script for i2code implement
#
# This script:
# 1. Archives files from a source repository at a given ref
# 2. Discovers the single idea in docs/features/
# 3. Copies config files (CLAUDE.md, settings.local.json)
# 4. Creates a GitHub repository under an organization
# 5. Runs i2code implement with real Claude Code
# 6. Verifies tasks are executed successfully
#
# Usage: test-i2code-implement.sh [options] <source-repo-path>
#
# Arguments:
#   source-repo-path  Path to an existing git repository containing an idea
#                     in docs/features/
#
# Options:
#   --ref REF         Git ref (tag, branch, HEAD) to archive from (default: HEAD)
#   --dry-run         Show what would be done without executing
#   --keep-repo       Don't delete the GitHub repo on exit (for debugging)
#   --setup-only      Only create repo and push, don't run i2code implement
#   --resume DIR      Resume execution in a previously created clone directory
#   --non-interactive Run Claude in non-interactive mode (uses -p flag)
#   --extra-prompt TEXT  Extra text to append to Claude's prompt
#   --isolate             Run inside an isolarium VM
#   --isolation-type TYPE Isolation environment type (passed as --isolation-type)
#   --skip-scaffolding    Skip the scaffolding step
#   --debug-claude        Show full Claude output instead of progress dots
#   -h, --help            Show this help message
#
# Environment:
#   GH_TEST_ORG       GitHub organization for repo creation
#                     (default: humansintheloop-test-org)
# HELP_END

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration paths
CONFIG_FILES_DIR="$PROJECT_ROOT/config-files"

# Test configuration
GH_TEST_ORG="${GH_TEST_ORG:-humansintheloop-test-org}"
CLEANUP_ON_EXIT=true
DRY_RUN=false
SETUP_ONLY=false
RESUME_DIR=""
NON_INTERACTIVE=false
EXTRA_PROMPT=""
ISOLATE=false
ISOLATION_TYPE=""
SKIP_SCAFFOLDING=false
DEBUG_CLAUDE=false
SOURCE_REPO_PATH=""
REF="HEAD"

# Discovered at runtime
IDEA_DIR=""
IDEA_NAME=""

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup tracking
GITHUB_REPO_FULL_NAME=""
CLONE_DIR=""

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

        if [ -n "$CLONE_DIR" ] && [ -d "$CLONE_DIR" ]; then
            log_info "Removing cloned directory: $CLONE_DIR"
            rm -rf "$CLONE_DIR"
        fi

        # Also clean up any worktree that was created
        if [ -n "$CLONE_DIR" ] && [ -n "$IDEA_NAME" ]; then
            local repo_name
            repo_name=$(basename "$CLONE_DIR")
            local worktree_dir
            worktree_dir="$(dirname "$CLONE_DIR")/${repo_name}-wt-${IDEA_NAME}"
            if [ -d "$worktree_dir" ]; then
                log_info "Removing worktree directory: $worktree_dir"
                rm -rf "$worktree_dir"
            fi
        fi
    else
        if [ -n "$GITHUB_REPO_FULL_NAME" ]; then
            log_warning "Keeping GitHub repository: $GITHUB_REPO_FULL_NAME"
        fi
        if [ -n "$CLONE_DIR" ]; then
            log_warning "Keeping cloned directory: $CLONE_DIR"
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
            --resume)
                RESUME_DIR="$2"
                CLEANUP_ON_EXIT=false
                shift 2
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            --extra-prompt)
                EXTRA_PROMPT="$2"
                shift 2
                ;;
            --isolate)
                ISOLATE=true
                shift
                ;;
            --isolation-type)
                ISOLATION_TYPE="$2"
                shift 2
                ;;
            --ref)
                REF="$2"
                shift 2
                ;;
            --skip-scaffolding)
                SKIP_SCAFFOLDING=true
                shift
                ;;
            --debug-claude)
                DEBUG_CLAUDE=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            -*)
                log_error "Unknown option: $1"
                show_help
                ;;
            *)
                SOURCE_REPO_PATH="$1"
                shift
                ;;
        esac
    done

    # Require source repo path unless resuming from worktree
    if [ -z "$SOURCE_REPO_PATH" ] && [ -z "$RESUME_DIR" ]; then
        log_error "Missing required argument: <source-repo-path>"
        echo ""
        show_help
    fi
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

    # Check required config files exist
    if [ ! -f "$CONFIG_FILES_DIR/CLAUDE.md" ]; then
        log_error "CLAUDE.md not found at $CONFIG_FILES_DIR/CLAUDE.md"
        exit 1
    fi

    if [ ! -f "$CONFIG_FILES_DIR/settings.local.json" ]; then
        log_error "settings.local.json not found at $CONFIG_FILES_DIR/settings.local.json"
        exit 1
    fi

    # Validate source repo path
    if [ ! -d "$SOURCE_REPO_PATH" ]; then
        log_error "Source repo path does not exist: $SOURCE_REPO_PATH"
        exit 1
    fi

    if [ ! -d "$SOURCE_REPO_PATH/.git" ]; then
        log_error "Source repo path is not a git repository: $SOURCE_REPO_PATH"
        exit 1
    fi

    if ! command -v i2code &> /dev/null; then
        log_error "i2code is not installed"
        exit 1
    fi

    log_success "All prerequisites satisfied"
}

is_mutable_ref() {
    local ref="$1"
    if [ "$ref" = "HEAD" ]; then
        return 0
    fi
    # Tags are immutable — branches are mutable
    if git -C "$SOURCE_REPO_PATH" show-ref --verify --quiet "refs/tags/$ref" 2>/dev/null; then
        return 1
    fi
    return 0
}

verify_pristine() {
    if ! is_mutable_ref "$REF"; then
        log_info "Ref '$REF' is a tag — skipping pristine check"
        return
    fi

    log_info "Verifying source repo has no uncommitted changes at '$REF'..."

    local diff
    diff=$(git -C "$SOURCE_REPO_PATH" diff "$REF")
    if [ -n "$diff" ]; then
        log_error "Source repo has uncommitted changes relative to '$REF'"
        exit 1
    fi

    local untracked
    untracked=$(git -C "$SOURCE_REPO_PATH" ls-files --others --exclude-standard)
    if [ -n "$untracked" ]; then
        log_error "Source repo has untracked files"
        exit 1
    fi

    log_success "Source repo is clean at '$REF'"
}

clone_repository() {
    log_info "Archiving source repository at ref '$REF'..."

    local source_abs
    source_abs="$(cd "$SOURCE_REPO_PATH" && pwd)"
    local source_basename
    source_basename="$(basename "$source_abs")"
    local source_parent
    source_parent="$(dirname "$source_abs")"

    local timestamp
    timestamp=$(date +%Y%m%d%H%M%S)
    local isolation_segment=""
    if [ -n "$ISOLATION_TYPE" ]; then
        isolation_segment="-${ISOLATION_TYPE}"
    fi
    local clone_name="${source_basename}-cl${isolation_segment}-${timestamp}"

    CLONE_DIR="${source_parent}/${clone_name}"

    mkdir -p "$CLONE_DIR"
    git -C "$SOURCE_REPO_PATH" archive "$REF" | tar xf - -C "$CLONE_DIR"
    cd "$CLONE_DIR"
    git init
    git add .
    git commit -m "Initial commit from $REF"

    log_success "Created repo from archive: $CLONE_DIR"
}

discover_idea() {
    log_info "Discovering idea by searching for *-plan.md files..."

    local plan_files=()
    while IFS= read -r -d '' file; do
        plan_files+=("$file")
    done < <(find "$CLONE_DIR/docs" -name "*-plan.md" -print0)

    if [ ${#plan_files[@]} -eq 0 ]; then
        log_error "No *-plan.md files found in repo"
        exit 1
    fi

    if [ ${#plan_files[@]} -gt 1 ]; then
        log_error "Multiple *-plan.md files found (expected exactly 1):"
        for f in "${plan_files[@]}"; do
            log_error "  ${f#"$CLONE_DIR"/}"
        done
        exit 1
    fi

    IDEA_DIR="$(dirname "${plan_files[0]}")"
    IDEA_NAME="$(basename "$IDEA_DIR")"

    log_success "Discovered idea: $IDEA_NAME"
}

copy_config_files() {
    log_info "Copying config files..."

    cp "$CONFIG_FILES_DIR/CLAUDE.md" "$CLONE_DIR/CLAUDE.md"
    log_info "  Copied CLAUDE.md"

    ln -s "$PROJECT_ROOT/.env.local" "$CLONE_DIR/.env.local"
    log_info "  Linked .env.local"

    mkdir -p "$CLONE_DIR/.claude"
    cp "$CONFIG_FILES_DIR/settings.local.json" "$CLONE_DIR/.claude/settings.local.json"
    log_info "  Copied settings.local.json"

    log_success "Config files copied"
}

commit_config_files() {
    log_info "Committing config files..."

    cd "$CLONE_DIR"
    git add CLAUDE.md
    git commit -m "Add config files for test run"

    log_success "Config files committed"
}

create_github_repo() {
    log_info "Creating GitHub repository under $GH_TEST_ORG..."

    local repo_name
    repo_name="$(basename "$CLONE_DIR")"

    cd "$CLONE_DIR"

    # Remove origin pointing to local source repo
    git remote remove origin 2>/dev/null || true

    if ! gh repo create "$GH_TEST_ORG/$repo_name" --private --source . --push; then
        log_error "Failed to create GitHub repository"
        exit 1
    fi

    GITHUB_REPO_FULL_NAME="$GH_TEST_ORG/$repo_name"

    log_success "GitHub repository created: $GITHUB_REPO_FULL_NAME"
}

run_implement_with_worktree() {
    log_info "Running i2code implement..."

    cd "$CLONE_DIR"

    # Build command with optional flags
    local cmd=("i2code" "implement")
    if [ "$ISOLATE" = true ]; then
        cmd+=("--isolate")
    fi
    if [ -n "$ISOLATION_TYPE" ]; then
        cmd+=("--isolation-type" "$ISOLATION_TYPE")
    fi
    if [ "$NON_INTERACTIVE" = true ]; then
        cmd+=("--non-interactive")
    fi
    if [ -n "$EXTRA_PROMPT" ]; then
        cmd+=("--extra-prompt" "$EXTRA_PROMPT")
    fi
    if [ "$SKIP_SCAFFOLDING" = true ]; then
        cmd+=("--skip-scaffolding")
    fi
    if [ "$DEBUG_CLAUDE" = true ]; then
        cmd+=("--debug-claude")
    fi
    cmd+=("$IDEA_DIR")

    log_info "Command: ${cmd[*]}"
    if [ "$ISOLATE" = true ] || [ -n "$ISOLATION_TYPE" ]; then
        which isolarium || { log_error "isolarium not found on PATH"; exit 1; }
        log_info "Destroying existing isolarium environment i2code-${IDEA_NAME} (if any)..."
        isolarium --name "i2code-${IDEA_NAME}" --type "$ISOLATION_TYPE" destroy 2>/dev/null || true
    fi

    # Remove .venv directories from PATH so that nono sandbox uses uv-tool-installed i2code
    PATH=$(echo "$PATH" | tr ':' '\n' | grep -v '\.venv' | paste -sd ':' -)
    "${cmd[@]}"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "i2code implement completed successfully"
    else
        log_error "i2code implement failed with exit code $exit_code"
        exit $exit_code
    fi
}

resume_from_clone() {
    log_info "Resuming from clone directory: $RESUME_DIR"

    if [ ! -d "$RESUME_DIR" ]; then
        log_error "Clone directory not found: $RESUME_DIR"
        exit 1
    fi

    CLONE_DIR="$RESUME_DIR"

    # Get GitHub repo name from git remote
    cd "$CLONE_DIR"
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$remote_url" ]; then
        GITHUB_REPO_FULL_NAME=$(echo "$remote_url" | sed -E 's|.*github.com[:/]([^/]+/[^/.]+).*|\1|')
        log_info "GitHub repository: $GITHUB_REPO_FULL_NAME"
    fi

    discover_idea

    log_success "Resume context loaded"
}

verify_results() {
    log_info "Verifying results..."

    cd "$CLONE_DIR"

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

setup_logging() {
    local log_dir="$PROJECT_ROOT/logs"
    mkdir -p "$log_dir"

    local repo_dir
    if [ -n "$SOURCE_REPO_PATH" ]; then
        repo_dir="$(basename "$SOURCE_REPO_PATH")"
    else
        repo_dir="$(basename "$RESUME_DIR")"
    fi

    local timestamp
    timestamp=$(date +%Y%m%d%H%M%S)
    local isolation_segment=""
    if [ -n "$ISOLATION_TYPE" ]; then
        isolation_segment="-${ISOLATION_TYPE}"
    fi
    local log_file="$log_dir/${repo_dir}-${REF}${isolation_segment}-${timestamp}.log"

    log_info "Logging output to $log_file"
    exec > >(tee "$log_file") 2>&1
}

main() {
    parse_args "$@"
    setup_logging

    echo ""
    echo "========================================="
    echo "  i2code implement E2E Test"
    echo "========================================="
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - Commands will not be executed"
        echo ""
        echo "Source repo: $SOURCE_REPO_PATH"
        echo "GitHub org:  $GH_TEST_ORG"
        echo ""
        echo "Ref:         $REF"
        echo ""
        echo "Would execute:"
        echo "  1. Archive $SOURCE_REPO_PATH at ref '$REF' to sibling directory"
        echo "  2. Discover idea in docs/features/"
        echo "  3. Copy CLAUDE.md and settings.local.json"
        echo "  4. Commit config files"
        echo "  5. Create GitHub repository under $GH_TEST_ORG"
        echo "  6. Run i2code implement"
        if [ -n "$EXTRA_PROMPT" ]; then
        echo "     with extra prompt: $EXTRA_PROMPT"
        fi
        echo "  7. Verify results"
        if [ "$CLEANUP_ON_EXIT" = true ]; then
        echo "  8. Clean up (delete GitHub repo and cloned directory)"
        else
        echo "  8. Keep GitHub repo and cloned directory (--keep-repo)"
        fi
        echo ""
        exit 0
    fi

    # Resume from existing worktree if specified
    if [ -n "$RESUME_DIR" ]; then
        resume_from_clone
        run_implement_with_worktree
        verify_results
        echo ""
        log_success "E2E test completed successfully!"
        echo ""
        exit 0
    fi

    check_prerequisites
    verify_pristine
    clone_repository
    discover_idea
    copy_config_files
    commit_config_files
    create_github_repo

    if [ "$SETUP_ONLY" = true ]; then
        log_warning "SETUP ONLY - Skipping i2code implement execution"
        log_info "Cloned directory: $CLONE_DIR"
        log_info "GitHub repository: $GITHUB_REPO_FULL_NAME"
        log_info "To run manually:"
        echo ""
        echo "  cd $CLONE_DIR"
        echo "  i2code implement $IDEA_DIR"
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
