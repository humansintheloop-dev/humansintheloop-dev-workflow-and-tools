# Specification: i2code go should grant permissions

## Purpose and background

Claude Code now prompts users to approve read access to the working directory. When `i2code go` invokes Claude for brainstorming, spec creation, design, and planning, this permission prompt interrupts the automated workflow. The user must manually approve read access each time Claude is launched, breaking the flow of the orchestrator's menu-driven experience.

## Target users

Developers using `i2code go` to move an idea through the brainstorm → spec → design → plan lifecycle.

## Problem statement

Each time `i2code go` launches Claude for a workflow step, Claude prompts the user to approve read access to the CWD. This is redundant friction — `i2code go` already knows what Claude needs access to and should grant it upfront.

## Goals

1. Eliminate the read-access permission prompt when Claude is invoked by `i2code go`.
2. Grant Claude write access to the idea directory so it can create/update idea, spec, discussion, and plan files.
3. Run Claude from the repository root so it can explore the full codebase for context.

## In scope

- The subcommands invoked by `i2code go`: brainstorm, spec create, spec revise, design create, plan create, plan revise.
- Adding `--allowedTools` CLI flags to the `claude` command for these subcommands.
- Changing the CWD from the idea directory to the repository root.

## Out of scope

- The `implement` step invoked by `i2code go` — it has its own permission system.
- Standalone commands (`i2code idea brainstorm`, `i2code spec create`, etc.) run outside of `i2code go`.
- Modifying `.claude/settings.local.json` or any persistent project files.

## Functional requirements

### FR1: Grant permissions via CLI flags

When `i2code go` invokes Claude for any in-scope subcommand, the `claude` command must include `--allowedTools` with:

- `Read(/<repo_root>/)` — read access to the repository root
- `Write(/<idea_dir>/)` — write access to the idea directory
- `Edit(/<idea_dir>/)` — edit access to the idea directory

Where:
- `<repo_root>` is the absolute path of the directory where `i2code` was invoked (i.e., `os.getcwd()` at startup).
- `<idea_dir>` is the absolute path of `project.directory`.

### FR2: Set CWD to repository root

All in-scope subcommands must invoke Claude with `cwd` set to the repository root instead of `project.directory`.

### FR3: Affected subcommands

The following functions currently build a `claude` command and pass `cwd=project.directory`:

| Function | File | Current CWD |
|----------|------|-------------|
| `brainstorm_idea()` | `src/i2code/idea_cmd/brainstorm.py` | `project.directory` |
| `create_spec()` | `src/i2code/spec_cmd/create_spec.py` | `project.directory` |
| `revise_spec()` | `src/i2code/spec_cmd/revise_spec.py` | `project.directory` |
| `create_plan()` via `_generate_plan()` | `src/i2code/go_cmd/create_plan.py` | `project.directory` |
| `revise_plan()` | `src/i2code/go_cmd/revise_plan.py` | `project.directory` |

All must change to use the repo root as CWD and include the `--allowedTools` flag.

### FR4: Command format

The resulting command for an interactive invocation should follow this pattern:

```
claude --allowedTools "Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)" <session_args> <prompt>
```

For batch invocations (e.g., `create_plan` which uses `-p`):

```
claude --allowedTools "Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)" -p <prompt>
```

## Non-functional requirements

- **Backward compatibility:** Standalone commands must continue to work as they do today — no changes to their behavior.
- **Testability:** The permission flags and CWD must be observable in tests without launching a real Claude process.

## Success metrics

- Running `i2code go <idea-dir>` through any workflow step does not prompt the user for read access.
- Claude can read files anywhere in the repo and write/edit files in the idea directory without prompts.

## Epics and user stories

### Epic: Grant permissions in i2code go

**US1:** As a developer running `i2code go`, when I select "Create idea", Claude launches without prompting me for read access.

**US2:** As a developer running `i2code go`, when I select "Create specification", Claude can read the codebase and write the spec file without permission prompts.

**US3:** As a developer running `i2code go`, when I select "Create implementation plan", Claude can read the codebase and write the plan file without permission prompts.

## Scenarios

### S1: Brainstorm a new idea (primary end-to-end scenario)

1. Developer runs `i2code go my-new-idea` from the repo root.
2. Orchestrator detects NO_IDEA state, launches brainstorm.
3. Editor opens for the user to describe the idea.
4. Claude is invoked with `--allowedTools "Read(/<repo_root>/),Write(/<idea_dir>/),Edit(/<idea_dir>/)"` and `cwd=<repo_root>`.
5. Claude reads the idea file and codebase files without prompting.
6. Claude writes the discussion file without prompting.

### S2: Create specification from existing idea

1. Developer runs `i2code go my-idea` from the repo root.
2. Orchestrator detects HAS_IDEA_NO_SPEC state, user selects "Create specification".
3. Claude is invoked with permission flags and `cwd=<repo_root>`.
4. Claude reads idea, discussion, and codebase files without prompting.
5. Claude writes the spec file without prompting.

### S3: Create implementation plan

1. Developer runs `i2code go my-idea` from the repo root.
2. Orchestrator detects HAS_SPEC state, user selects "Create implementation plan".
3. Claude is invoked in batch mode with permission flags and `cwd=<repo_root>`.
4. Claude reads idea, spec, and codebase files without prompting.
5. Claude writes the plan file without prompting.

### S4: Revise spec or plan

1. Developer runs `i2code go my-idea` from the repo root.
2. User selects "Revise the specification" or "Revise the plan".
3. Claude is invoked with permission flags and `cwd=<repo_root>`.
4. Claude reads and edits existing files without prompting.
