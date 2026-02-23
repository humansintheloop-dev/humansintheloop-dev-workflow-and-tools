#!/bin/bash
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to detect current workflow state using _helper.sh variables
detect_state() {
    # Check file existence in order of workflow progression
    if ! ls "$IDEA_FILE" >/dev/null 2>&1; then
        echo "no_idea"
    elif [[ ! -f "$SPEC_FILE" ]]; then
        echo "has_idea_no_spec"
    elif [[ ! -f "$PLAN_WITHOUT_STORIES_FILE" ]]; then
        echo "has_spec"
    elif [[ -f "$PLAN_WITHOUT_STORIES_FILE" ]]; then
        echo "has_plan"
    else
        echo "complete"
    fi
}

# Function to run a workflow step
run_step() {
    local description="$1"
    shift
    local cmd=("$@")

    echo ""
    echo "$description..."
    echo ""

    # Execute the command
    if "${cmd[@]}"; then
        return 0
    else
        local exit_code=$?
        echo ""
        echo "Error: Failed to execute ${cmd[*]} (exit code: $exit_code)"
        return $exit_code
    fi
}

# Function to display menu and get user choice
get_user_choice() {
    local prompt="$1"
    local default="$2"
    shift 2
    local options=("$@")
    
    # Display menu to stderr so it shows even when function output is captured
    echo "" >&2
    echo "$prompt" >&2
    for i in "${!options[@]}"; do
        if [ "$((i+1))" -eq "$default" ]; then
            echo "  $((i+1))) ${options[$i]} [default]" >&2
        else
            echo "  $((i+1))) ${options[$i]}" >&2
        fi
    done
    echo "" >&2
    
    local choice
    local prompt_text="Enter your choice (1-${#options[@]})"
    if [ -n "$default" ]; then
        prompt_text="$prompt_text [default: $default]"
    fi
    prompt_text="$prompt_text: "
    
    while true; do
        read -r -p "$prompt_text" choice || {
            # Handle EOF (e.g., when input is piped)
            echo "" >&2
            echo "Input closed. Exiting." >&2
            exit 0
        }
        # If empty and default exists, use default
        if [ -z "$choice" ] && [ -n "$default" ]; then
            echo "$default"
            return 0
        fi
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "$choice"
            return 0
        else
            echo "Invalid choice. Please enter a number between 1 and ${#options[@]}." >&2
        fi
    done
}

# Function to check for uncommitted changes in a directory
has_uncommitted_changes() {
    local dir="$1"
    local status_output
    status_output=$(git status --porcelain -- "$dir")
    [ -n "$status_output" ]
}

# Function to commit uncommitted idea changes in a directory
commit_idea_changes() {
    local dir="$1"
    echo "Committing idea changes..."
    git add "$dir"
    git commit -m "Add idea docs for $IDEA_NAME" -- "$dir"
}

# Function to handle errors with retry option
handle_error() {
    echo ""
    echo "What would you like to do?"
    local choice
    choice=$(get_user_choice "Options:" 1 "Retry" "Abort workflow")
    
    case "$choice" in
        1)
            return 0  # Signal to retry
            ;;
        2)
            echo "Workflow aborted."
            exit 1
            ;;
    esac
}

# Trap Ctrl+C
trap 'echo ""; echo "Workflow interrupted."; exit 130' INT

# Function to prompt user for implement configuration options
prompt_implement_config() {
    local mode_choice
    mode_choice=$(get_user_choice "How should Claude run?" 1 "Interactive" "Non-interactive")
    if [ "$mode_choice" -eq 1 ]; then
        IMPLEMENT_INTERACTIVE=true
    else
        IMPLEMENT_INTERACTIVE=false
    fi

    local branch_choice
    branch_choice=$(get_user_choice "Where should implementation happen?" 1 "Worktree (branch + PR)" "Trunk (current branch, no PR)")
    if [ "$branch_choice" -eq 1 ]; then
        IMPLEMENT_TRUNK=false
    else
        IMPLEMENT_TRUNK=true
    fi
}

# Function to write implement configuration to file
write_implement_config() {
    printf 'interactive: %s\ntrunk: %s\n' "$IMPLEMENT_INTERACTIVE" "$IMPLEMENT_TRUNK" > "$IMPLEMENT_CONFIG_FILE"
}

# Function to read implement configuration from file
read_implement_config() {
    IMPLEMENT_INTERACTIVE=$(sed -n 's/^interactive: *//p' "$IMPLEMENT_CONFIG_FILE")
    IMPLEMENT_TRUNK=$(sed -n 's/^trunk: *//p' "$IMPLEMENT_CONFIG_FILE")
    IMPLEMENT_INTERACTIVE="${IMPLEMENT_INTERACTIVE:-true}"
    IMPLEMENT_TRUNK="${IMPLEMENT_TRUNK:-false}"
}

# Function to build flags for i2code implement based on config
build_implement_flags() {
    IMPLEMENT_FLAGS=()
    if [ "$IMPLEMENT_INTERACTIVE" = "false" ]; then
        IMPLEMENT_FLAGS+=(--non-interactive)
    fi
    if [ "$IMPLEMENT_TRUNK" = "true" ]; then
        IMPLEMENT_FLAGS+=(--trunk)
    fi
}

# Main function
main() {
    local dir="$1"
    
    # Validate parameters
    if [[ $# -ne 1 ]]; then
        echo "Usage: $0 <directory>"
        echo ""
        echo "This script orchestrates the idea-to-code workflow."
        echo "Provide a directory that contains (or will contain) your workflow files."
        exit 1
    fi
    
    # Check if directory exists
    if [[ ! -d "$dir" ]]; then
        echo "Directory does not exist: $dir"
        echo ""
        read -r -p "Would you like to create it? (y/N): " create_dir
        
        if [[ "$create_dir" =~ ^[Yy]$ ]]; then
            if mkdir -p "$dir"; then
                echo "Directory created successfully: $dir"
                echo ""
            else
                echo "Error: Failed to create directory: $dir"
                exit 1
            fi
        else
            echo "Directory creation cancelled."
            echo "Please create the directory manually or provide a valid directory path."
            exit 1
        fi
    fi
    
    # Source helper to set up environment variables
    # This sets IDEA_FILE, SPEC_FILE, STORY_FILE, PLAN_WITHOUT_STORIES_FILE, PLAN_WITH_STORIES_FILE, etc.
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/_helper.sh" "$dir"

    # Display initial status
    echo "================================================"
    echo "  Idea-to-Code Workflow Orchestrator"
    echo "================================================"
    echo ""
    echo "Working directory: $dir"
    echo "Project name: $IDEA_NAME"
    echo ""
    
    # Main workflow loop
    while true; do
        # Re-source helper to pick up files created by previous steps
        # (e.g. brainstorm-idea.sh may create .md when IDEA_FILE defaulted to .txt)
        # shellcheck disable=SC1091
        source "$SCRIPT_DIR/_helper.sh" "$dir"

        local state
        state=$(detect_state)
        
        echo "Current state: $state ($dir)"
        
        case "$state" in
            no_idea)
                echo ""
                echo "No idea file found. Starting workflow..."
                if run_step "Step 1: Creating idea" "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"; then
                    echo "Idea created successfully!"
                else
                    if handle_error "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"; then
                        continue  # Retry
                    fi
                fi
                ;;
                
            has_idea_no_spec)
                local choice
                choice=$(get_user_choice "Idea exists. What would you like to do?" 2 \
                    "Revise idea" \
                    "Create specification" \
                    "Exit")
                
                case "$choice" in
                    1)
                        if run_step "Revising idea" "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"; then
                            echo "Idea revised successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    2)
                        if run_step "Step 2: Creating specification" "$SCRIPT_DIR/make-spec.sh" "$dir"; then
                            echo "Specification created successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/make-spec.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    3)
                        echo "Exiting workflow."
                        exit 0
                        ;;
                esac
                ;;
                
            has_spec)
                local choice
                choice=$(get_user_choice "Specification created. What would you like to do?" 2 \
                    "Revise the specification" \
                    "Create implementation plan" \
                    "Exit")

                case "$choice" in
                    1)
                        if run_step "Revising specification" "$SCRIPT_DIR/revise-spec.sh" "$dir"; then
                            echo "Specification revised successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/revise-spec.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    2)
                        if run_step "Creating implementation plan" "$SCRIPT_DIR/make-plan.sh" "$dir"; then
                            echo "Implementation plan created successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/make-plan.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    3)
                        echo "Exiting workflow."
                        exit 0
                        ;;
                esac
                ;;
                
            has_plan)
                local choice
                if has_uncommitted_changes "$dir"; then
                    choice=$(get_user_choice "Implementation plan exists. What would you like to do?" 2 \
                        "Revise the plan" \
                        "Commit changes" \
                        "Implement the entire plan" \
                        "Exit")

                    case "$choice" in
                        1)
                            if run_step "Revising plan" "$SCRIPT_DIR/revise-plan.sh" "$dir"; then
                                echo "Plan revised successfully!"
                            else
                                if handle_error "$SCRIPT_DIR/revise-plan.sh" "$dir"; then
                                    continue  # Retry
                                fi
                            fi
                            ;;
                        2)
                            if commit_idea_changes "$dir"; then
                                echo "Changes committed successfully!"
                                continue
                            else
                                if handle_error "git commit" "$dir"; then
                                    continue  # Retry
                                fi
                            fi
                            ;;
                        3)
                            if [ ! -f "$IMPLEMENT_CONFIG_FILE" ]; then
                                prompt_implement_config
                                write_implement_config
                            fi
                            read_implement_config
                            build_implement_flags
                            if run_step "Implementing plan" i2code implement "${IMPLEMENT_FLAGS[@]}" "$dir"; then
                                echo "Implementation completed successfully!"
                                echo ""
                                if grep -q '\[ \]' "$PLAN_WITHOUT_STORIES_FILE" 2>/dev/null; then
                                    echo "================================================"
                                    echo "  Plan has uncompleted tasks"
                                    echo "================================================"
                                    echo ""
                                else
                                    echo "================================================"
                                    echo "  Workflow Complete!"
                                    echo "================================================"
                                    exit 0
                                fi
                            else
                                if handle_error "i2code implement" "$dir"; then
                                    continue  # Retry
                                fi
                            fi
                            ;;
                        4)
                            echo "Exiting workflow."
                            exit 0
                            ;;
                    esac
                else
                    choice=$(get_user_choice "Implementation plan exists. What would you like to do?" 2 \
                        "Revise the plan" \
                        "Implement the entire plan" \
                        "Exit")

                    case "$choice" in
                        1)
                            if run_step "Revising plan" "$SCRIPT_DIR/revise-plan.sh" "$dir"; then
                                echo "Plan revised successfully!"
                            else
                                if handle_error "$SCRIPT_DIR/revise-plan.sh" "$dir"; then
                                    continue  # Retry
                                fi
                            fi
                            ;;
                        2)
                            if [ ! -f "$IMPLEMENT_CONFIG_FILE" ]; then
                                prompt_implement_config
                                write_implement_config
                            fi
                            read_implement_config
                            build_implement_flags
                            if run_step "Implementing plan" i2code implement "${IMPLEMENT_FLAGS[@]}" "$dir"; then
                                echo "Implementation completed successfully!"
                                echo ""
                                if grep -q '\[ \]' "$PLAN_WITHOUT_STORIES_FILE" 2>/dev/null; then
                                    echo "================================================"
                                    echo "  Plan has uncompleted tasks"
                                    echo "================================================"
                                    echo ""
                                else
                                    echo "================================================"
                                    echo "  Workflow Complete!"
                                    echo "================================================"
                                    exit 0
                                fi
                            else
                                if handle_error "i2code implement" "$dir"; then
                                    continue  # Retry
                                fi
                            fi
                            ;;
                        3)
                            echo "Exiting workflow."
                            exit 0
                            ;;
                    esac
                fi
                ;;
                
            complete)
                echo ""
                echo "================================================"
                echo "  Workflow appears to be complete!"
                echo "================================================"
                echo ""
                echo "All expected files are present in the project directory."
                exit 0
                ;;
                
            *)
                echo "Error: Unknown state: $state"
                exit 1
                ;;
        esac
    done
}

# Run main function with all arguments
main "$@"