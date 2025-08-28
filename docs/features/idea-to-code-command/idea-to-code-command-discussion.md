# idea-to-code Command Discussion

## Initial Idea
Implement an idea-to-code.sh script in workflow-scripts that takes the user through the idea to code workflow. It has a single parameter that's the directory containing the workflow files. On startup it should determine what steps of the workflow have been completed, and resume the workflow at the correct point by running the appropriate script. If there is a choice, it should prompt the user which option to do next.

## Q&A Session

### Question 1: Workflow Step Detection
**Q:** How should the script detect which workflow steps have been completed? Should it:

A) Check for the existence of specific output files (e.g., *-idea.txt, *-spec.md, *-plan.md files)
B) Maintain a hidden state file (.workflow-state) that tracks completed steps
C) Parse git history to see which files were created/modified
D) Use file timestamps to determine the order and completion of steps

**Default suggestion:** Option A - Check for existence of specific output files, as this is simplest and aligns with the file-based nature of the workflow.

**A:** Option A - Check for the existence of specific output files.

### Question 2: Workflow Steps Definition
**Q:** Which workflow steps should the script recognize and orchestrate? Based on the existing scripts in workflow-scripts, should it handle:

A) idea → spec → plan → implement (linear flow)
B) idea → spec → (plan OR implement) → test (branching flow)
C) Custom workflow defined in a configuration file
D) All scripts found in workflow-scripts directory dynamically

**Default suggestion:** Option A - A linear flow of idea → spec → plan → implement, as this represents the most common and straightforward development path.

**A:** Option A - The linear flow: idea → spec → plan → implement (as documented in docs/idea-to-code-workflow.adoc)

### Question 3: Script Mapping
**Q:** How should the script map workflow steps to actual scripts? Should it:

A) Use hardcoded script names: brainstorm-idea.sh, make-spec.sh, make-plan.sh, implement-plan.sh
B) Use a naming convention pattern: *-idea.sh, *-spec.sh, *-plan.sh, *-implement.sh
C) Look for a mapping file that defines step → script relationships
D) Auto-detect scripts based on their shebang comments or metadata

**Default suggestion:** Option A - Use the hardcoded script names (brainstorm-idea.sh, make-spec.sh, make-plan.sh, implement-plan.sh) as these are the established scripts in the workflow.

**A:** Option A - Use hardcoded script names from workflow-scripts/ directory

### Question 4: Revision/Alternative Paths
**Q:** How should the script handle revision steps (revise-spec.sh, revise-plan.sh) and alternative paths (make-stories.sh, make-story-plan.sh)? Should it:

A) Ignore them - only support the main linear flow
B) After each main step, ask if the user wants to revise before proceeding
C) Detect if revision files exist and offer to run revision scripts
D) Support parallel tracks (stories track vs direct plan track) as user choice

**Default suggestion:** Option B - After completing each main step, ask if the user wants to revise it before moving to the next step.

**A:** Custom approach:
- After creating a spec: ask if the user wants to (a) revise spec, (b) create stories, or (c) proceed to plan
- After creating stories: continue to story-plan → implement-story-plan
- After creating a plan: ask if the user wants to revise before implementing
- If spec exists but no plan: offer to revise spec or create plan

### Question 5: User Interface
**Q:** How should the script interact with the user when presenting choices? Should it:

A) Use simple bash read prompts with numbered options (1, 2, 3)
B) Use dialog/whiptail for terminal UI menus
C) Use select bash builtin for menu selection
D) Use fzf or similar fuzzy finder for interactive selection

**Default suggestion:** Option A - Simple bash read prompts with numbered options for maximum portability.

**A:** Option A - Simple bash read prompts with numbered options

### Question 6: Error Handling
**Q:** How should the script handle errors when a workflow script fails? Should it:

A) Exit immediately with error code
B) Ask user if they want to retry, skip, or abort
C) Log error and continue with next available step
D) Automatically retry once, then ask for user input

**Default suggestion:** Option B - Ask the user if they want to retry the failed step, skip to next step, or abort the workflow.

**A:** Option B - Ask user if they want to retry, skip, or abort

### Question 7: Progress Display
**Q:** How should the script display workflow progress and status? Should it:

A) Simple text output: "Step 2 of 4: Creating specification..."
B) ASCII progress bar with percentage
C) Colored output with status indicators (✓ complete, → in progress, ○ pending)
D) Minimal output - only show current action

**Default suggestion:** Option C - Colored output with status indicators for clear visual feedback.

**A:** Option A - Simple text output since each step runs an interactive command (claude), so displaying simple progress before running script is sufficient

### Question 8: Script Location
**Q:** How should the script locate the workflow-scripts directory? Should it:

A) Assume it's in the same directory as idea-to-code.sh
B) Use a WORKFLOW_SCRIPTS_DIR environment variable
C) Search parent directories for workflow-scripts/
D) Accept it as an optional second parameter (with default to same directory)

**Default suggestion:** Option A - Assume workflow-scripts is in the same directory as idea-to-code.sh for simplicity.

**A:** Option A - Assume it's in the same directory as idea-to-code.sh

### Question 9: File Naming Convention
**Q:** What naming pattern should the script expect for workflow files? Currently you mentioned checking for files like:

A) [directory-name]-idea.txt, [directory-name]-spec.md, [directory-name]-plan.md
B) idea.txt, spec.md, plan.md (simple names)
C) [project-name]-[step].* (any extension)
D) Match the base name from the directory parameter

**Default suggestion:** Option A - Use [directory-name]-idea.txt pattern, extracting the prefix from the last component of the directory path.

**A:** Option A - Use the existing naming scheme from _helper.sh: [basename]-idea.txt, [basename]-spec.md, [basename]-plan.md, [basename]-stories.md, [basename]-story-plan.md

### Question 10: Script Name and Installation
**Q:** What should the script be called and where should it be installed? Should it be:

A) idea-to-code.sh in workflow-scripts/ directory
B) workflow.sh in workflow-scripts/ directory  
C) idea-to-code as a standalone executable in the user's PATH
D) itc (short name) in workflow-scripts/ directory

**Default suggestion:** Option A - idea-to-code.sh in the workflow-scripts/ directory, consistent with other workflow scripts.

**A:** Option A - idea-to-code.sh in workflow-scripts/ directory

## Summary

Based on our discussion, here's the complete specification for the idea-to-code.sh script:

### Core Functionality
- **Purpose**: Orchestrate the idea-to-code workflow by detecting completed steps and running appropriate scripts
- **Location**: workflow-scripts/idea-to-code.sh
- **Parameter**: Single required parameter - directory containing workflow files

### Workflow Detection
- Check for existence of specific output files to determine completed steps
- File naming: [basename]-idea.txt, [basename]-spec.md, [basename]-plan.md, [basename]-stories.md, [basename]-story-plan.md
- Extract basename from the last component of the directory path

### Workflow Flow
1. **Idea stage**: If no idea file exists, run brainstorm-idea.sh
2. **Spec stage**: After idea exists, run make-spec.sh
   - Then offer choices: (a) revise spec, (b) create stories, (c) proceed to plan
3. **Stories path** (optional): 
   - If user chooses stories, run make-stories.sh
   - Then continue to make-story-plan.sh → implement-story-plan.sh
4. **Plan path**: 
   - Run make-plan.sh
   - Offer to revise before implementing
5. **Implementation**: Run implement-plan.sh (or implement-story-plan.sh if stories path taken)

### User Interface
- Simple bash read prompts with numbered options
- Display progress as simple text: "Step X of Y: [Description]..."
- Each script runs interactively with claude, so minimal UI needed

### Error Handling
- When a workflow script fails, ask user to:
  - Retry the failed step
  - Skip to next step
  - Abort the workflow

### Script Discovery
- Assume workflow-scripts directory is in same location as idea-to-code.sh
- Use hardcoded script names: brainstorm-idea.sh, make-spec.sh, make-plan.sh, implement-plan.sh, revise-spec.sh, revise-plan.sh, make-stories.sh, make-story-plan.sh, implement-story-plan.sh
