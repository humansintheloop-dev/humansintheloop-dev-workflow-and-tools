# idea-to-code.sh Specification

## Overview

The `idea-to-code.sh` script is a workflow orchestrator that guides users through the complete idea-to-code development process. It intelligently detects which workflow steps have been completed and resumes at the appropriate point, offering choices for revision and alternative paths.

## Requirements

### Functional Requirements

1. **Workflow State Detection**
   - Detect completed workflow steps by checking for existence of output files
   - Resume workflow at the correct point based on existing files
   - Support both linear and branching workflow paths

2. **User Interaction**
   - Present clear options to users at decision points
   - Allow users to choose between revision, alternative paths, or continuation
   - Handle user input gracefully with validation

3. **Script Execution**
   - Execute appropriate workflow scripts based on current state
   - Pass correct parameters to each script
   - Handle script execution errors appropriately

4. **Progress Tracking**
   - Display current workflow position
   - Show what steps have been completed
   - Indicate next available actions

### Non-Functional Requirements

1. **Portability**
   - Use standard bash features available on most Unix-like systems
   - Avoid dependencies on external tools not commonly installed
   - Work with the existing workflow scripts without modification

2. **Maintainability**
   - Clear, readable code structure
   - Consistent with existing workflow script patterns
   - Reuse existing helper functions where possible

3. **User Experience**
   - Minimal, clear output that doesn't overwhelm
   - Intuitive prompts and error messages
   - Quick startup with immediate feedback

## Architecture

### File Structure
```
workflow-scripts/
├── idea-to-code.sh          # Main orchestrator script
├── _helper.sh               # Shared helper functions (existing)
├── brainstorm-idea.sh       # Step 1: Create idea
├── make-spec.sh             # Step 2: Create specification
├── revise-spec.sh           # Optional: Revise specification
├── make-stories.sh          # Alternative path: Create stories
├── make-story-plan.sh       # Story path: Create story plan
├── implement-story-plan.sh  # Story path: Implement stories
├── make-plan.sh             # Direct path: Create plan
├── revise-plan.sh           # Optional: Revise plan
└── implement-plan.sh        # Direct path: Implement plan
```

### Workflow State Machine

```
START
  |
  v
[No idea.txt] → brainstorm-idea.sh
  |
  v
[idea.txt exists, no spec.md] → CHOICE:
  |                              ├─ Revise idea → brainstorm-idea.sh → (loop back)
  |                              └─ Create spec → make-spec.sh
  |
  v
[spec.md exists] → CHOICE:
  |                 ├─ Revise spec → revise-spec.sh → (loop back)
  |                 ├─ Create stories → make-stories.sh
  |                 └─ Create plan → make-plan.sh
  |
  v
[stories.md exists] → make-story-plan.sh
  |
  v
[story-plan.md exists] → implement-story-plan.sh
  |
  v
[plan.md exists] → CHOICE:
  |                 ├─ Revise plan → revise-plan.sh → (loop back)
  |                 └─ Implement → implement-plan.sh
  |
  v
END
```

## Data Handling

### Input Parameters
- **Required**: Directory path containing workflow files
  - Must be a valid directory
  - Will be passed to all workflow scripts

### File Naming Convention
Based on the existing `_helper.sh` patterns:
- Extract basename from directory path (last component)
- File patterns:
  - `[basename]-idea.txt` - Initial idea description
  - `[basename]-spec.md` - Specification document
  - `[basename]-plan.md` - Implementation plan
  - `[basename]-stories.md` - User stories (optional path)
  - `[basename]-story-plan.md` - Story-based plan (optional path)

### State Detection Logic
```bash
# Pseudo-code for state detection
if [[ ! -f "$dir/$basename-idea.txt" ]]; then
    state="no_idea"
elif [[ ! -f "$dir/$basename-spec.md" ]]; then
    state="has_idea_no_spec"
elif [[ -f "$dir/$basename-stories.md" ]] && [[ ! -f "$dir/$basename-story-plan.md" ]]; then
    state="has_stories"
elif [[ -f "$dir/$basename-story-plan.md" ]] && [[ ! -f "implementation_marker" ]]; then
    state="has_story_plan"
elif [[ ! -f "$dir/$basename-plan.md" ]] && [[ ! -f "$dir/$basename-stories.md" ]]; then
    state="has_spec"
elif [[ -f "$dir/$basename-plan.md" ]] && [[ ! -f "implementation_marker" ]]; then
    state="has_plan"
else
    state="complete"
fi
```

## User Interface

### Prompts and Menus
Use simple numbered menus with bash `read` command:

```bash
# Example prompt structure
echo "Specification created successfully!"
echo ""
echo "What would you like to do next?"
echo "  1) Revise the specification"
echo "  2) Create user stories"
echo "  3) Create implementation plan"
echo "  4) Exit"
echo ""
read -p "Enter your choice (1-4): " choice
```

### Progress Display
Simple text output before running each script:
```
Step 2 of 4: Creating specification...
```

### Error Messages
Clear, actionable error messages:
```
Error: Failed to create specification.

What would you like to do?
  1) Retry
  2) Abort workflow
```

## Error Handling

### Script Execution Errors
1. Capture exit code from each workflow script
2. On non-zero exit:
   - Display error message
   - Offer options: retry or abort
   - Log the error for debugging

### Input Validation
- Validate directory parameter exists
- Validate user menu choices are within valid range
- Handle Ctrl+C gracefully with trap

### Recovery Strategy
- Failed steps must be retried or workflow aborted (no skipping)
- Preserve all existing files (never delete user work)
- Provide clear feedback about what went wrong

## Implementation Details

### Script Structure
```bash
#!/bin/bash
set -e  # Exit on error (with proper handling)

# Source helper functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_helper.sh"

# Validate parameters
if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# Main workflow logic
main() {
    local dir="$1"
    local basename=$(get_basename "$dir")
    
    while true; do
        local state=$(detect_state "$dir" "$basename")
        
        case "$state" in
            no_idea)
                run_step "Creating idea" "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"
                ;;
            has_idea_no_spec)
                echo "Idea exists. What would you like to do?"
                echo "  1) Revise idea"
                echo "  2) Create specification"
                echo "  3) Exit"
                read -p "Enter your choice (1-3): " choice
                case "$choice" in
                    1) run_step "Revising idea" "$SCRIPT_DIR/brainstorm-idea.sh" "$dir" ;;
                    2) run_step "Creating specification" "$SCRIPT_DIR/make-spec.sh" "$dir" ;;
                    3) exit 0 ;;
                esac
                ;;
            has_spec)
                offer_spec_choices "$dir"
                ;;
            # ... other states
            complete)
                echo "Workflow complete!"
                exit 0
                ;;
        esac
    done
}

main "$@"
```

### Integration with Existing Scripts
- Source `_helper.sh` for common functions
- Use same parameter passing convention (directory as first argument)
- Respect existing file naming patterns
- Don't modify behavior of existing scripts

## Testing Plan

### Manual Testing Checklist
- [ ] Run with no existing files
- [ ] Run with existing idea file
- [ ] Run with existing spec file
- [ ] Choose revision option for spec
- [ ] Choose stories path
- [ ] Choose direct plan path
- [ ] Test Ctrl+C at various points
- [ ] Test with invalid directory
- [ ] Test retry on script failure
- [ ] Complete full workflow end-to-end

## Deployment

### Installation
1. Place `idea-to-code.sh` in `workflow-scripts/` directory
2. Ensure execute permissions: `chmod +x idea-to-code.sh`
3. Verify all required workflow scripts are present

### Dependencies
- Bash 4.0 or higher
- Standard Unix utilities (basename, dirname, test)
- All existing workflow scripts in same directory
- Claude CLI (for workflow scripts to execute)

### Usage
```bash
# Basic usage
./workflow-scripts/idea-to-code.sh /path/to/project/directory

# From within workflow-scripts directory
./idea-to-code.sh ../docs/features/my-feature
```

## Future Enhancements

### Potential Improvements (Not in Initial Scope)
1. Configuration file for custom workflow definitions
2. Parallel execution of independent steps
3. Web UI for workflow visualization
4. Integration with git for automatic commits at each step
5. Workflow templates for different project types
6. Dry-run mode to preview workflow steps
7. Verbose mode for debugging
8. Resume from specific step flag

## Notes for Developers

### Key Considerations
1. The script acts as an orchestrator, not implementing any workflow logic itself
2. Each workflow script is responsible for its own validation and error handling
3. The orchestrator should be resilient to changes in workflow scripts
4. User data (files) should never be deleted or overwritten without confirmation
5. The script should be idempotent - running it multiple times should be safe

### Code Style Guidelines
- Follow existing bash script conventions in workflow-scripts/
- Use meaningful variable names
- Add comments for complex logic
- Keep functions small and focused
- Use local variables in functions
- Quote all variable expansions
- Use [[ ]] for conditionals, not [ ]

### Maintenance Notes
- When adding new workflow steps, update the state detection logic
- When changing file naming patterns, coordinate with _helper.sh
- Test thoroughly when modifying the state machine
- Document any changes to the workflow in the main documentation