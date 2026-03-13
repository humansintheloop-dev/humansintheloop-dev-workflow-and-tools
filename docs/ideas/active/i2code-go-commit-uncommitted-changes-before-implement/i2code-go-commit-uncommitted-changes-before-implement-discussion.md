# Discussion: Commit Uncommitted Changes Before Implement

## Classification

**Type: A. User-facing feature**

**Rationale**: This enhances the interactive `i2code go` workflow that the user directly interacts with. It adds a new menu option and git status check to an existing user-facing CLI orchestrator.

## Questions and Answers

### Q1: Should the uncommitted-changes check apply only in `has_plan` state, or at every loop iteration?

**Answer**: Only in `has_plan` — it only matters when invoking `i2code implement`.

### Q2: What should the commit mechanism be?

**Answer**: Invoke `claude -p "Commit the changes in the <idea-directory>"`. This delegates commit message generation and staging to Claude's commit guidelines.

### Q3: Should the scope of the uncommitted-changes check be limited to files inside the idea directory, or the entire repo?

**Answer**: Only files inside the idea directory.

### Q4: How should the commit option be presented?

**Answer**: "Commit changes" should be one of the multiple-choice options in the `has_plan` menu, not a separate prompt. It should be the default when uncommitted changes exist.

Menu with uncommitted changes:
1. Revise the plan
2. Commit changes [default]
3. Implement the entire plan
4. Exit

Menu without uncommitted changes (unchanged):
1. Revise the plan
2. Implement the entire plan [default]
3. Exit

### Q5: After the commit succeeds, what should happen?

**Answer**: Loop back to the top of the workflow (re-detect state, show the menu again). On the next iteration, if no more uncommitted changes remain, Implement will be the default.
