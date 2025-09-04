#!/bin/bash
set -e

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to detect current workflow state using _helper.sh variables
detect_state() {
    # Check file existence in order of workflow progression
    # IDEA_FILE can be either .txt or .md and may contain wildcards
    if ! ls $IDEA_FILE >/dev/null 2>&1; then
        echo "no_idea"
    elif [[ ! -f "$SPEC_FILE" ]]; then
        echo "has_idea_no_spec"
    elif [[ -f "$STORY_FILE" ]] && [[ ! -f "$PLAN_WITH_STORIES_FILE" ]]; then
        echo "has_stories"
    elif [[ -f "$PLAN_WITH_STORIES_FILE" ]]; then
        echo "has_story_plan"
    elif [[ ! -f "$PLAN_WITHOUT_STORIES_FILE" ]] && [[ ! -f "$STORY_FILE" ]]; then
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
    local script="$2"
    local dir="$3"
    
    echo ""
    echo "$description..."
    echo ""
    
    # Execute the script
    if "$script" "$dir"; then
        return 0
    else
        local exit_code=$?
        echo ""
        echo "Error: Failed to execute $script (exit code: $exit_code)"
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
        read -p "$prompt_text" choice || {
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

# Function to handle errors with retry option
handle_error() {
    local script="$1"
    local dir="$2"
    
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
        local state=$(detect_state)
        
        echo "Current state: $state"
        
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
                choice=$(get_user_choice "Specification created. What would you like to do?" 3 \
                    "Revise the specification" \
                    "Create user stories" \
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
                        if run_step "Creating user stories" "$SCRIPT_DIR/make-stories.sh" "$dir"; then
                            echo "User stories created successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/make-stories.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    3)
                        if run_step "Creating implementation plan" "$SCRIPT_DIR/make-plan.sh" "$dir"; then
                            echo "Implementation plan created successfully!"
                        else
                            if handle_error "$SCRIPT_DIR/make-plan.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    4)
                        echo "Exiting workflow."
                        exit 0
                        ;;
                esac
                ;;
                
            has_stories)
                echo ""
                echo "User stories found. Creating story-based plan..."
                if run_step "Creating story-based plan" "$SCRIPT_DIR/make-story-plan.sh" "$dir"; then
                    echo "Story-based plan created successfully!"
                else
                    if handle_error "$SCRIPT_DIR/make-story-plan.sh" "$dir"; then
                        continue  # Retry
                    fi
                fi
                ;;
                
            has_story_plan)
                local choice
                choice=$(get_user_choice "Story-based plan exists. What would you like to do?" 1 \
                    "Implement the story plan" \
                    "Exit")
                
                case "$choice" in
                    1)
                        if run_step "Implementing story-based plan" "$SCRIPT_DIR/implement-story-plan.sh" "$dir"; then
                            echo "Story-based implementation completed successfully!"
                            echo ""
                            # Check if plan has uncompleted tasks
                            if grep -q '\[ \]' "$PLAN_WITH_STORIES_FILE" 2>/dev/null; then
                                echo "================================================"
                                echo "  Plan has uncompleted tasks"
                                echo "================================================"
                                echo ""
                                # Continue the loop to show options again
                            else
                                echo "================================================"
                                echo "  Workflow Complete!"
                                echo "================================================"
                                exit 0
                            fi
                        else
                            if handle_error "$SCRIPT_DIR/implement-story-plan.sh" "$dir"; then
                                continue  # Retry
                            fi
                        fi
                        ;;
                    2)
                        echo "Exiting workflow."
                        exit 0
                        ;;
                esac
                ;;
                
            has_plan)
                local choice
                choice=$(get_user_choice "Implementation plan exists. What would you like to do?" 2 \
                    "Revise the plan" \
                    "Implement the plan" \
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
                        if run_step "Implementing plan" "$SCRIPT_DIR/implement-plan.sh" "$dir"; then
                            echo "Implementation completed successfully!"
                            echo ""
                            # Check if plan has uncompleted tasks
                            if grep -q '\[ \]' "$PLAN_WITHOUT_STORIES_FILE" 2>/dev/null; then
                                echo "================================================"
                                echo "  Plan has uncompleted tasks"
                                echo "================================================"
                                echo ""
                                # Continue the loop to show options again
                            else
                                echo "================================================"
                                echo "  Workflow Complete!"
                                echo "================================================"
                                exit 0
                            fi
                        else
                            if handle_error "$SCRIPT_DIR/implement-plan.sh" "$dir"; then
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