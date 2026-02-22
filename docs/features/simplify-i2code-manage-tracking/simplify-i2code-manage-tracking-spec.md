# Specification: Simplify i2code manage-tracking

## Purpose and Background

The `i2code` CLI provides a `manage-tracking` command that sets up HITL (human-in-the-loop) tracking directories for session and issue recording. The current command requires the user to explicitly pass `--migrate` and/or `--link DIR` flags, making it unnecessarily verbose for the common case where migration is always desired.

This feature simplifies the command by:
1. Renaming it to `i2code tracking setup` for a cleaner namespace.
2. Making migration the default behavior (removing the `--migrate` flag).
3. Extending subdirectory consolidation to handle `.hitl/` directories (not just legacy `.claude/` directories).

## Target Users and Personas

- **Developer using i2code**: A developer who runs `i2code tracking setup` in a project directory to configure HITL tracking. They expect a single command that "just works" without needing to remember multiple flags.

## Problem Statement and Goals

**Problem**: The current `i2code manage-tracking` command requires the user to pass `--migrate` explicitly even though migration is always the intended behavior. The command name is also awkward — `manage-tracking` is a verb-noun compound that doesn't fit well with other `i2code` subcommands.

Additionally, if a subdirectory already has a `.hitl/` directory (new format) with real files rather than symlinks to the top-level, the current command ignores it. This leaves tracking data fragmented across subdirectories.

**Goals**:
1. Simplify the CLI interface by making migration the default.
2. Provide a cleaner command namespace (`tracking setup`).
3. Consolidate all tracking data — including subdirectory `.hitl/` directories — into the top-level `.hitl/`.

## In-Scope

- Rename CLI command from `i2code manage-tracking` to `i2code tracking setup`
- Remove the `--migrate` flag — migration always runs
- Preserve `--link DIR` and `--dry-run` as optional flags
- Extend `_migrate_subdirectories` to consolidate subdirectory `.hitl/` real directories (merge contents + replace with relative symlinks)
- Remove the old `manage-tracking` command entirely (no deprecated alias)
- Update all documentation references
- Update tests for new command structure

## Out-of-Scope

- Additional subcommands under `tracking` (e.g., `tracking status`, `tracking reset`)
- Changes to session/issue file formats
- Changes to the `--link` behavior beyond what already exists
- Any specification or implementation planning (covered in later steps)

## High-Level Functional Requirements

### FR-1: Command Restructuring

The CLI entry point changes from:
```
i2code manage-tracking --migrate [--link DIR] [--dry-run]
```
to:
```
i2code tracking setup [--link DIR] [--dry-run]
```

`tracking` is a Click command group. `setup` is its only subcommand.

### FR-2: Default Migration Behavior

Running `i2code tracking setup` (with no flags) performs all migration steps:
1. Create `.hitl/{sessions,issues}` directories.
2. Update `.gitignore`: add `.hitl/{sessions,issues}` ignores, remove `.claude/{sessions,issues}` ignores.
3. Move contents of `.claude/{sessions,issues}` to `.hitl/{sessions,issues}`.
4. Consolidate subdirectory `.claude/` directories (legacy format) into top-level `.hitl/` with relative symlinks (existing behavior).
5. Consolidate subdirectory `.hitl/` real directories (new format) into top-level `.hitl/` with relative symlinks (new behavior).

### FR-3: Subdirectory `.hitl/` Consolidation

When a subdirectory contains a `.hitl/{sessions,issues}` directory that is a real directory (not a symlink):
1. Merge its contents into the top-level `.hitl/{sessions,issues}`.
2. Replace the subdirectory's `.hitl/{sessions,issues}` with relative symlinks pointing to the top-level.

This mirrors the existing behavior for legacy `.claude/` subdirectories.

### FR-4: Optional `--link DIR`

When `--link DIR` is specified (after migration completes):
- If top-level `.hitl/{sessions,issues}` are already symlinks to subdirs of `DIR` — no-op.
- If top-level `.hitl/{sessions,issues}` are real directories — move contents to subdirs of `DIR`, replace with symlinks.
- If top-level `.hitl/{sessions,issues}` are symlinks to a different directory — raise an error, make no changes.

### FR-5: `--dry-run`

When `--dry-run` is specified, the command prints what it would do without making any changes.

### FR-6: Idempotency

The command is fully idempotent. Running it repeatedly on an already-set-up project produces informational output and makes no changes. No errors are raised.

### FR-7: Old Command Removal

The `manage-tracking` command is removed entirely. No deprecated alias is provided.

## Security Requirements

| Operation | Who Can Perform | Authorization | Constraints |
|-----------|----------------|---------------|-------------|
| `i2code tracking setup` | Any developer with write access to the project directory | Local filesystem permissions | Operates only on the current working directory |
| `--link DIR` | Any developer with write access to both project dir and `DIR` | Local filesystem permissions | `DIR` must be writable |

No network access, authentication, or role-based authorization is involved. Security is governed entirely by local filesystem permissions.

## Non-Functional Requirements

### Usability
- The command should print clear, human-readable output describing each action taken (or skipped if idempotent).
- `--dry-run` output should be distinguishable from actual execution output.

### Reliability
- The command must not leave the project in a broken state if interrupted. File moves should be atomic where possible (same filesystem).
- If `--link DIR` detects a conflict (symlinks pointing to a different directory), it must error cleanly without partial changes.

### Performance
- No performance requirements beyond "completes in a few seconds for a typical project."

## Success Metrics

1. A developer can run `i2code tracking setup` with no flags and have a fully configured tracking directory.
2. Subdirectory `.hitl/` real directories are consolidated on first run.
3. Repeated runs produce no errors and no unintended side effects.
4. All documentation accurately reflects the new command name.

## Epics and User Stories

### Epic 1: CLI Restructuring

**US-1.1**: As a developer, I can run `i2code tracking setup` to set up HITL tracking, so that I don't need to remember the `--migrate` flag.

**US-1.2**: As a developer, I can run `i2code tracking setup --link DIR` to set up tracking with external linking in a single command.

**US-1.3**: As a developer, I can run `i2code tracking setup --dry-run` to preview what changes would be made without modifying anything.

### Epic 2: Subdirectory `.hitl/` Consolidation

**US-2.1**: As a developer, when I run `i2code tracking setup` and a subdirectory has a real `.hitl/` directory, its contents are merged into the top-level `.hitl/` and replaced with symlinks.

### Epic 3: Idempotency

**US-3.1**: As a developer, I can run `i2code tracking setup` repeatedly without errors or unintended side effects.

### Epic 4: Documentation and Cleanup

**US-4.1**: As a developer, I can find accurate documentation for `i2code tracking setup` in the project docs and README.

**US-4.2**: As a developer, I do not see the old `manage-tracking` command in `i2code --help` output.

## User-Facing Scenarios

### Scenario 1: Fresh Setup (Primary End-to-End Scenario)

A developer clones a project that has no `.hitl/` directory and no legacy `.claude/{sessions,issues}`. They run:
```
i2code tracking setup
```
**Expected**: `.hitl/{sessions,issues}` directories are created. `.gitignore` is updated. Informational output confirms setup.

### Scenario 2: Legacy Migration

A developer has an existing project with `.claude/{sessions,issues}` files. They run:
```
i2code tracking setup
```
**Expected**: Contents of `.claude/{sessions,issues}` are moved to `.hitl/{sessions,issues}`. `.gitignore` is updated (old ignores removed, new ignores added). Legacy files in subdirectories are consolidated with symlinks.

### Scenario 3: Subdirectory `.hitl/` Consolidation (New Behavior)

A developer has subdirectories with real `.hitl/{sessions,issues}` directories (not symlinks). They run:
```
i2code tracking setup
```
**Expected**: Subdirectory `.hitl/` contents are merged into top-level `.hitl/`. Subdirectory `.hitl/{sessions,issues}` are replaced with relative symlinks to the top-level.

### Scenario 4: Setup with External Linking

A developer wants tracking data stored in an external directory. They run:
```
i2code tracking setup --link /shared/tracking
```
**Expected**: Migration runs first, then `.hitl/{sessions,issues}` contents are moved to `/shared/tracking/{sessions,issues}` and replaced with symlinks.

### Scenario 5: Idempotent Re-run

A developer runs `i2code tracking setup` on a project that is already fully set up. They run it again:
```
i2code tracking setup
```
**Expected**: Informational output (e.g., "Nothing to migrate", "Already set up"). No errors. No changes.

### Scenario 6: Dry Run

A developer wants to preview what `tracking setup` would do:
```
i2code tracking setup --dry-run
```
**Expected**: Output describes what would happen without making changes.

### Scenario 7: Link Conflict

A developer has `.hitl/{sessions,issues}` symlinked to `/old/path`. They run:
```
i2code tracking setup --link /new/path
```
**Expected**: Error message indicating the existing symlinks point to a different directory. No changes made.
