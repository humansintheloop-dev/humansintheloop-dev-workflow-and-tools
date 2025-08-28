# idea-to-code.sh Implementation Plan

**STATUS: Core Implementation Complete** ✅  
The main functionality has been successfully implemented. Steel Threads 1-8 are complete.
Steel Thread 9 contains optional enhancements that can be added later as needed.

## Overview
This plan implements the idea-to-code.sh workflow orchestrator script using the Steel Thread methodology. Each thread delivers a narrow, end-to-end flow that provides immediate value to users.

## Instructions for Coding Agent
- Mark each checkbox with '[x]' when the task or step is completed
- Run tests after implementing each feature
- Refactor as needed while keeping tests passing
- Commit after each successful thread completion

## Steel Thread 1: Basic Script Setup and Directory Validation

### Purpose
Setup the foundational script structure with proper parameter validation and helper function integration.

### Implementation Steps

```text
[x] Create workflow-scripts/idea-to-code.sh with proper shebang and permissions
    [x] Add #!/bin/bash shebang
    [x] Set file permissions to executable (chmod +x)
    [x] Add set -e for error handling

[x] Write test for directory parameter validation
    [x] Test with no parameters (should show usage and exit)
    [x] Test with non-existent directory (should error)
    [x] Test with valid directory (should proceed)

[x] Implement parameter validation
    [x] Check parameter count equals 1
    [x] Display usage message if incorrect: "Usage: $0 <directory>"
    [x] Validate directory exists using [[ -d "$dir" ]]
    [x] Exit with error code 1 on validation failure

[x] Write test for helper script integration
    [x] Test that _helper.sh is sourced correctly
    [x] Test that get_basename function is available

[x] Source _helper.sh and setup script directory
    [x] Calculate SCRIPT_DIR using dirname and cd/pwd pattern
    [x] Source "$SCRIPT_DIR/_helper.sh"
    [x] Handle missing _helper.sh gracefully

[x] Refactor and ensure clean code structure
    [x] Organize code into logical sections
    [x] Add appropriate error messages
```

## Steel Thread 2: State Detection for No Idea File

### Purpose
Detect when no idea file exists and execute the brainstorm-idea.sh script.

### Implementation Steps

```text
[x] Write test for detecting no-idea state
    [x] Create test directory without any workflow files
    [x] Test that state detection identifies "no_idea" state
    [x] Test that correct file path pattern is checked

[x] Implement detect_state function
    [x] Extract basename using get_basename from _helper.sh
    [x] Check for $dir/$basename-idea.txt existence
    [x] Return "no_idea" state when file doesn't exist
    [x] Add function documentation

[x] Write test for executing brainstorm-idea.sh
    [x] Mock/stub brainstorm-idea.sh execution
    [x] Test that script is called with correct directory parameter
    [x] Test handling of successful execution (exit code 0)

[x] Implement main workflow loop
    [x] Create main() function with directory parameter
    [x] Add while loop for continuous workflow
    [x] Call detect_state to determine current state
    [x] Add case statement for state handling

[x] Implement no_idea state handler
    [x] Display "Step 1: Creating idea..." message
    [x] Execute "$SCRIPT_DIR/brainstorm-idea.sh" "$dir"
    [x] Check exit code and handle errors
    [x] Loop back to state detection after success

[x] Write test for error handling
    [x] Test script execution failure (non-zero exit code)
    [x] Test missing brainstorm-idea.sh script
    [x] Test user retry option

[x] Add error handling for script execution
    [x] Capture exit code from brainstorm-idea.sh
    [x] Display error message on failure
    [x] Offer retry or abort options
    [x] Implement retry logic
```

## Steel Thread 3: Idea Exists, Spec Creation Choice

### Purpose
When an idea file exists but no spec, offer user choice to revise idea or create specification.

### Implementation Steps

```text
[x] Write test for detecting has_idea_no_spec state
    [x] Create test with existing idea.txt but no spec.md
    [x] Test state detection returns "has_idea_no_spec"
    [x] Test file existence checks are correct

[x] Update detect_state function
    [x] Add check for spec.md file existence
    [x] Return "has_idea_no_spec" when idea exists but spec doesn't
    [x] Maintain proper state precedence

[x] Write test for user menu display
    [x] Test menu shows correct options
    [x] Test input validation for choices 1-3
    [x] Test invalid input handling

[x] Implement interactive menu for idea state
    [x] Display "Idea exists. What would you like to do?"
    [x] Show numbered options:
        1) Revise idea
        2) Create specification  
        3) Exit
    [x] Use read -p for user input
    [x] Validate input is within range

[x] Write test for choice execution
    [x] Test choice 1 executes brainstorm-idea.sh
    [x] Test choice 2 executes make-spec.sh
    [x] Test choice 3 exits cleanly

[x] Implement choice handlers
    [x] Choice 1: Call brainstorm-idea.sh with directory
    [x] Choice 2: Call make-spec.sh with directory
    [x] Choice 3: Exit with code 0
    [x] Invalid input: Re-display menu

[x] Add run_step helper function
    [x] Extract common script execution pattern
    [x] Display step message before execution
    [x] Handle exit codes consistently
    [x] Return to main loop after execution
```

## Steel Thread 4: Specification Exists, Three-Way Choice

### Purpose
When specification exists, offer choices for revision, stories path, or direct plan creation.

### Implementation Steps

```text
[x] Write test for detecting has_spec state
    [x] Create test with existing spec.md, no plan or stories
    [x] Test state detection returns "has_spec"
    [x] Test proper precedence with other states

[x] Update detect_state for has_spec
    [x] Check spec.md exists
    [x] Check stories.md doesn't exist
    [x] Check plan.md doesn't exist
    [x] Return "has_spec" state

[x] Write test for spec menu display
    [x] Test three-way choice menu
    [x] Test all valid inputs (1-4)
    [x] Test invalid input handling

[x] Implement spec choice menu
    [x] Display "Specification created. What would you like to do?"
    [x] Show options:
        1) Revise the specification
        2) Create user stories
        3) Create implementation plan
        4) Exit
    [x] Validate user input

[x] Write test for spec choice execution
    [x] Test revise-spec.sh execution (choice 1)
    [x] Test make-stories.sh execution (choice 2)
    [x] Test make-plan.sh execution (choice 3)
    [x] Test clean exit (choice 4)

[x] Implement spec choice handlers
    [x] Choice 1: Execute revise-spec.sh
    [x] Choice 2: Execute make-stories.sh
    [x] Choice 3: Execute make-plan.sh
    [x] Choice 4: Exit cleanly
    [x] Loop back after script execution
```

## Steel Thread 5: Stories Path Implementation

### Purpose
Handle the alternative workflow path through user stories and story-based planning.

### Implementation Steps

```text
[x] Write test for stories path states
    [x] Test has_stories state detection
    [x] Test has_story_plan state detection
    [x] Test correct state transitions

[x] Update detect_state for stories path
    [x] Add check for stories.md existence
    [x] Add check for story-plan.md existence
    [x] Return appropriate states:
        - "has_stories" when stories exist but no story-plan
        - "has_story_plan" when story-plan exists

[x] Write test for automatic story-plan creation
    [x] Test that make-story-plan.sh is called automatically
    [x] Test no user prompt needed
    [x] Test error handling

[x] Implement has_stories state handler
    [x] Display "Creating story-based plan..."
    [x] Execute make-story-plan.sh automatically
    [x] Handle execution errors
    [x] Progress to next state

[x] Write test for story-plan implementation
    [x] Test implement-story-plan.sh execution
    [x] Test completion detection
    [x] Test error handling

[x] Implement has_story_plan state handler
    [x] Display "Implementing story-based plan..."
    [x] Execute implement-story-plan.sh
    [x] Mark as complete after success
    [x] Handle execution errors
```

## Steel Thread 6: Direct Plan Path with Revision

### Purpose
Handle the direct implementation plan path with revision option.

### Implementation Steps

```text
[x] Write test for plan states
    [x] Test has_plan state detection
    [x] Test plan revision choice
    [x] Test implementation choice

[x] Update detect_state for plan path
    [x] Check for plan.md existence
    [x] Ensure not in stories path
    [x] Return "has_plan" state

[x] Write test for plan menu
    [x] Test revision vs implementation choice
    [x] Test input validation
    [x] Test exit option

[x] Implement plan choice menu
    [x] Display "Implementation plan created. What would you like to do?"
    [x] Show options:
        1) Revise the plan
        2) Implement the plan
        3) Exit
    [x] Validate user input

[x] Write test for plan choice execution
    [x] Test revise-plan.sh execution
    [x] Test implement-plan.sh execution
    [x] Test clean exit

[x] Implement plan choice handlers
    [x] Choice 1: Execute revise-plan.sh
    [x] Choice 2: Execute implement-plan.sh
    [x] Choice 3: Exit cleanly
    [x] Loop appropriately after execution
```

## Steel Thread 7: Progress Display and User Experience

### Purpose
Add clear progress tracking and improved user feedback throughout the workflow.

### Implementation Steps

```text
[x] Write test for progress display
    [x] Test step numbering logic
    [x] Test progress messages
    [x] Test completion message

[x] Implement step counter
    [x] Track current step number
    [x] Calculate total steps based on path
    [x] Display "Step X of Y: [Action]..."

[x] Write test for status summary
    [x] Test initial status display
    [x] Test file existence reporting
    [x] Test clear formatting

[x] Add workflow status display
    [x] Show existing files on startup
    [x] Display current workflow position
    [x] Show available next actions
    [x] Use consistent formatting

[x] Improve error messages
    [x] Add specific error context
    [x] Suggest resolution actions
    [x] Maintain consistent tone

[x] Add completion handling
    [x] Detect when workflow is complete
    [x] Display success message
    [x] Exit cleanly
```

## Steel Thread 8: Robust Error Handling and Recovery

### Purpose
Implement comprehensive error handling with retry logic and graceful interruption.

### Implementation Steps

```text
[x] Write test for interrupt handling
    [x] Test Ctrl+C during script execution
    [x] Test Ctrl+C during user input
    [x] Test cleanup on interrupt

[x] Implement signal trapping
    [x] Add trap for SIGINT
    [x] Display interruption message
    [x] Clean exit without partial state

[x] Write test for retry mechanism
    [x] Test retry on script failure
    [x] Test retry limit
    [x] Test abort option

[x] Implement retry logic
    [x] Track retry attempts
    [x] Offer retry after failures
    [x] Limit maximum retries
    [x] Provide abort option

[x] Write test for script availability
    [x] Test missing workflow scripts
    [x] Test permission errors
    [x] Test helpful error messages

[x] Add script validation
    [x] Check all required scripts exist
    [x] Verify execute permissions
    [x] Report specific missing scripts
    [x] Suggest installation steps

[x] Write test for edge cases
    [x] Test empty directory name
    [x] Test special characters in paths
    [x] Test very long paths

[x] Handle edge cases
    [x] Sanitize directory paths
    [x] Handle spaces in filenames
    [x] Validate basename extraction
    [x] Add defensive checks
```

## Steel Thread 9: Configuration and Deployment

### Purpose
Finalize script configuration, add help system, and prepare for deployment.

### Implementation Steps

```text
[ ] Write test for help system
    [ ] Test -h flag shows help
    [ ] Test --help flag shows help
    [ ] Test help content completeness

[ ] Implement help display
    [ ] Add -h/--help flag handling
    [ ] Show usage information
    [ ] Describe workflow steps
    [ ] List available options

[ ] Write test for version information
    [ ] Test --version flag
    [ ] Test version format

[ ] Add version information
    [ ] Define VERSION variable
    [ ] Handle --version flag
    [ ] Display version clearly

[ ] Write integration tests
    [ ] Test complete workflow from no files
    [ ] Test resume from each state
    [ ] Test both workflow paths
    [ ] Test all user choices

[ ] Add logging capability
    [ ] Log to ~/.idea-to-code.log
    [ ] Include timestamps
    [ ] Log state transitions
    [ ] Log script executions

[ ] Create installation documentation
    [ ] Document prerequisites
    [ ] Provide installation steps
    [ ] Include usage examples
    [ ] Add troubleshooting guide

[ ] Final cleanup and optimization
    [ ] Remove debug code
    [ ] Optimize state detection
    [ ] Ensure consistent style
    [ ] Add final comments
```

## Testing Strategy

### Unit Testing
Each steel thread includes test-first development:
1. Write failing test
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Commit when all tests pass

### Integration Testing
After completing all threads:
1. Test full workflow end-to-end
2. Test all decision branches
3. Test error recovery paths
4. Test with real workflow scripts

### Manual Testing Checklist
[x] Fresh start (no existing files)
[x] Resume from each state
[x] All menu choices
[x] Error conditions
[x] Interrupt handling
[ ] Help and version flags (not implemented - optional enhancement)

## Implementation Notes

### Key Design Decisions
1. State detection based on file existence for simplicity and reliability
2. Interactive menus using standard bash read command
3. Reuse of existing _helper.sh functions
4. No modification of existing workflow scripts
5. Clear separation between orchestration and workflow logic

### Code Quality Guidelines
- Follow existing bash conventions in workflow-scripts/
- Use [[ ]] for conditionals
- Quote all variable expansions
- Use local variables in functions
- Add meaningful error messages
- Keep functions focused and small

## Change History

(Initially empty - changes will be recorded here during implementation)