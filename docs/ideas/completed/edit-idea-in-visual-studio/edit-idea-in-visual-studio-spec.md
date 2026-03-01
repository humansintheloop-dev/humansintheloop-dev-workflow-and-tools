# Edit Idea in Visual Studio Code — Specification

## Purpose and Background

The `i2code go` command orchestrates the idea-to-code workflow. When no idea file exists, the `brainstorm-idea.sh` script creates a `.txt` file with placeholder text and opens it in `vi`. This forces all users into a terminal-based editor regardless of their preferred environment.

Developers who use VS Code as their primary editor lose access to markdown preview, extensions, and familiar keybindings when authoring idea files. This feature enhances the editor selection logic to prefer VS Code when available, with graceful fallback through standard Unix editor conventions.

## Target Users

Developers using the `i2code go` workflow to brainstorm and refine ideas — primarily VS Code users who want a richer editing experience for idea files.

## Problem Statement

The current implementation hardcodes `vi` as the editor for new idea files. This is a poor default for developers who primarily use graphical editors, and it ignores the established Unix convention of `$VISUAL` / `$EDITOR` environment variables.

## Goals

1. Open new idea files in VS Code when available, giving users markdown preview and a familiar editing environment.
2. Respect standard Unix editor conventions (`$VISUAL`, `$EDITOR`) as fallbacks.
3. Use `.md` format when VS Code is the editor to take advantage of its markdown capabilities.
4. Preserve the existing post-edit behavior (auto-launch Claude brainstorm session).

## In Scope

- Editor resolution logic in `brainstorm-idea.sh`
- Conditional file extension selection (`.md` vs `.txt`) based on resolved editor
- Blocking behavior (`code --wait`) so the script waits for the user to finish editing

## Out of Scope

- Changes to `idea-to-code.sh` menu flow or confirmation prompts
- Changes to `_helper.sh` (already supports both `.txt` and `.md`)
- Changes to the Claude brainstorm session behavior
- Editor selection for revising existing idea files (only applies to initial creation)
- VS Code extension recommendations or workspace configuration

## Functional Requirements

### FR-1: Editor Resolution

When no idea file exists and the script needs to open an editor, resolve the editor using this priority order:

1. `code --wait` — if the `code` command is found on `$PATH`
2. `$VISUAL` — if set and non-empty
3. `$EDITOR` — if set and non-empty
4. `vi` — final fallback

The resolution stops at the first match.

### FR-2: Conditional File Extension

The idea file extension depends on the resolved editor:

| Resolved Editor | File Extension |
|----------------|---------------|
| `code` (VS Code) | `.md` |
| Any other editor | `.txt` |

### FR-3: VS Code Invocation

When VS Code is the resolved editor, invoke it as:

```
code --wait <file>
```

No additional flags.

### FR-4: Blocking Behavior

The script must block until the user closes or saves the file in the editor, regardless of which editor is selected. For VS Code, this is handled by `--wait`. For terminal editors (`vi`, `nano`, etc.), this is the default behavior.

### FR-5: Placeholder Content

The placeholder content written to the new idea file remains unchanged: `"PLEASE DESCRIBE YOUR IDEA"`. This applies regardless of file extension.

### FR-6: Post-Edit Behavior

After the editor closes, the existing behavior continues unchanged: the script proceeds to launch a Claude brainstorm session using the idea file content.

## Non-Functional Requirements

### NFR-1: Backward Compatibility

On systems without VS Code and without `$VISUAL`/`$EDITOR` set, the behavior must be identical to today (creates `.txt`, opens in `vi`).

### NFR-2: Simplicity

The implementation should be minimal — a small change to `brainstorm-idea.sh` with no new files or dependencies.

### NFR-3: Responsiveness

Editor detection (checking `$PATH` for `code`) should add negligible latency to the workflow.

## Success Metrics

- VS Code users see their idea file open in VS Code with markdown formatting.
- Users without VS Code experience no change in behavior.
- The brainstorm session launches correctly regardless of which editor was used.

## Epics and User Stories

### Epic: Improved Editor Selection for Idea Creation

**US-1:** As a developer with VS Code installed, when I run `i2code go` on a new idea directory, I want the idea file to open in VS Code as a `.md` file so I can use markdown preview while writing my idea.

**US-2:** As a developer without VS Code, when I run `i2code go` on a new idea directory, I want the idea file to open in my preferred editor (`$VISUAL` or `$EDITOR`) so I'm not forced into `vi`.

**US-3:** As a developer with no editor preferences set and no VS Code, when I run `i2code go` on a new idea directory, I want the idea file to open in `vi` as a `.txt` file, preserving the current behavior.

## Scenarios

### Scenario 1 (Primary): VS Code available on PATH

**Given** the idea file does not exist
**And** `code` is found on `$PATH`
**When** `brainstorm-idea.sh` runs
**Then** a new `.md` idea file is created with placeholder content
**And** `code --wait <file>` opens the file
**And** the script blocks until the user closes the file in VS Code
**And** the Claude brainstorm session launches with the idea file content

### Scenario 2: VS Code not available, $VISUAL set

**Given** the idea file does not exist
**And** `code` is NOT on `$PATH`
**And** `$VISUAL` is set (e.g., to `subl -w`)
**When** `brainstorm-idea.sh` runs
**Then** a new `.txt` idea file is created with placeholder content
**And** the file opens in the `$VISUAL` editor
**And** the script blocks until the user finishes editing
**And** the Claude brainstorm session launches

### Scenario 3: Fallback to $EDITOR

**Given** the idea file does not exist
**And** `code` is NOT on `$PATH`
**And** `$VISUAL` is not set
**And** `$EDITOR` is set (e.g., to `nano`)
**When** `brainstorm-idea.sh` runs
**Then** a new `.txt` idea file is created with placeholder content
**And** the file opens in the `$EDITOR` editor
**And** the Claude brainstorm session launches after editing

### Scenario 4: Final fallback to vi

**Given** the idea file does not exist
**And** `code` is NOT on `$PATH`
**And** `$VISUAL` is not set
**And** `$EDITOR` is not set
**When** `brainstorm-idea.sh` runs
**Then** a new `.txt` idea file is created with placeholder content
**And** `vi` opens the file
**And** the Claude brainstorm session launches after editing

### Scenario 5: Idea file already exists

**Given** the idea file already exists (`.txt` or `.md`)
**When** `brainstorm-idea.sh` runs
**Then** the editor selection logic is skipped entirely
**And** the existing brainstorm session resumes as it does today
