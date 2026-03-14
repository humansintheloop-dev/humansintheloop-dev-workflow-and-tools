# Edit Idea in Visual Studio Code - Discussion

## Context

Currently, `brainstorm-idea.sh` creates a `.txt` idea file and opens it in `vi` when no idea file exists. The proposal is to enhance `i2code go` to open the idea file in VS Code using `code --wait` instead, and to use `.md` format.

## Questions and Answers

### Q1: When `code` is NOT on the PATH, what should happen?

**Options:**
- A. Fall back to `vi` (current behavior)
- B. Fall back to the `$EDITOR` environment variable, then `vi` as last resort
- C. Show an error message and exit (require VS Code)
- D. Prompt the user to choose an editor

**Answer:** B. Fall back to `$EDITOR`, then `vi` as last resort.

**Decision:** Editor resolution order is: `code --wait` (if on PATH) → `$VISUAL` → `$EDITOR` → `vi`.

### Q2: Should the idea file format change from `.txt` to `.md`?

**Options:**
- A. Always create as `.md` regardless of editor
- B. Create as `.md` only when VS Code is selected, `.txt` otherwise
- C. Let the user choose the format

**Answer:** B. Create as `.md` when VS Code is the editor, `.txt` otherwise.

**Decision:** File format is tied to editor selection — `.md` for VS Code, `.txt` for other editors.

### Q3: Should the Claude brainstorm session still auto-launch after the editor closes?

**Options:**
- A. Auto-launch Claude brainstorm session after editor closes (current behavior)
- B. Return to the `i2code go` menu, letting the user choose next step

**Answer:** A. Keep current behavior — auto-launch brainstorm after editor closes.

### Q4: Should there be a new confirmation prompt before creating the idea file?

The idea mentions "the user confirms they want to create it" as a precondition. Currently, `idea-to-code.sh` doesn't ask — it directly calls `brainstorm-idea.sh` in the `no_idea` state. The confirmation only exists for directory creation.

**Options:**
- A. Add an explicit "Create idea file?" confirmation
- B. The existing flow is sufficient — implicit confirmation

**Answer:** B. The existing flow is sufficient as implicit confirmation.

### Q5: Should `code --wait` include any additional flags?

**Options:**
- A. Plain: `code --wait <file>`
- B. With new window: `code --wait --new-window <file>`
- C. With reuse: `code --wait --reuse-window <file>`

**Answer:** A. Plain `code --wait <file>`. Keep it simple.

## Classification

**Type:** A. User-facing feature

**Rationale:** This modifies the user-facing behavior of the `i2code go` command — specifically how developers interact with the editor when creating a new idea file. The change affects the CLI workflow UX rather than infrastructure, architecture, or educational content.
