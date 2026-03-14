# i2code go should grant permissions

## Problem

Claude Code now prompts for read access to the CWD. When `i2code go` invokes Claude for brainstorming, spec creation, design, and planning, this permission prompt interrupts the workflow.

## Solution

The subcommands invoked by `i2code go` (brainstorm, spec, design, plan) should pass permission flags on the Claude command line:

- **Read** access to the repository root (where `i2code` was run from)
- **Write/Edit** access to the idea directory

Additionally, Claude should be invoked with CWD set to the repository root (not the idea directory as it is today), so it can naturally explore the codebase.

## Scope

- Only affects subcommands invoked by `i2code go` — not `implement` (which has its own permission system) and not standalone commands.
- Permissions are passed via `--allowedTools` CLI flags (transient, no project file modifications).
