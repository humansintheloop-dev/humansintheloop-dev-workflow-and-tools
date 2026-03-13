# Specification: Support Isolarium Type

## Purpose and Background

The `i2code implement` command supports three execution modes: trunk, worktree, and isolate. The isolate mode delegates work to an **isolarium** VM via the `isolarium` CLI. Today, the isolarium command is invoked with a fixed structure:

```
isolarium --name i2code-<feature> run [--interactive] -- i2code --with-sdkman implement --isolated <idea-dir> [options...]
```

The isolarium CLI supports a `--type TYPE` global option that selects which kind of isolation environment to create (e.g., different VM images or container runtimes). Currently, `i2code implement` has no way to pass this option through, forcing users to always get the default isolation type.

This feature adds an `--isolation-type TYPE` option to `i2code implement` that maps directly to isolarium's `--type TYPE`.

## Target Users and Personas

**Developer using `i2code implement --isolate`** — A developer who runs automated implementation workflows inside isolated environments and needs to select a specific isolation type (e.g., a different VM image or container configuration) based on the project's requirements.

## Problem Statement

When a developer needs a non-default isolation environment, there is no way to specify the isolation type through `i2code implement`. The developer must either:
1. Manually construct the isolarium command (bypassing `i2code implement` entirely), or
2. Accept the default isolation type regardless of project needs.

## Goals

1. Allow developers to specify an isolation type when running `i2code implement`.
2. Make the UX ergonomic: specifying an isolation type should imply isolation mode without requiring `--isolate` as well.
3. Keep the implementation minimal — pass through to isolarium without duplicating validation.

## In-Scope

- Add `--isolation-type TYPE` option to `i2code implement` CLI
- Pass the value through as `--type TYPE` in the isolarium global args
- When `--isolation-type` is specified, automatically enable isolate mode (`--isolate` implied)
- Flow the option through the command assembler pattern: `cli.py` → `ImplementOpts` → `ImplementCommand` → `ModeFactory` → `IsolateMode`
- Unit tests following existing patterns (fakes, class-per-behavior, pytest marks)

## Out-of-Scope

- Adding `--isolation-type` to `i2code scaffold` (future work)
- Validating isolation type values (isolarium handles its own validation)
- Providing a default isolation type (isolarium has its own default)
- Changes to isolarium itself

## High-Level Functional Requirements

### FR-1: CLI Option

Add `--isolation-type TYPE` as an optional Click option on the `implement` command. The option accepts a string value (the isolation type name). When omitted, no `--type` argument is passed to isolarium (preserving current behavior).

### FR-2: Implied Isolation

When `--isolation-type` is provided but `--isolate` is not, automatically enable isolate mode. The developer does not need to pass both flags.

### FR-3: Isolarium Command Construction

In `IsolateMode._build_isolarium_command()`, when an isolation type is provided, insert `--type TYPE` into the isolarium global arguments (before the subcommand `run`). The resulting command structure:

```
isolarium --name i2code-<feature> --type <type> run [--interactive] -- i2code --with-sdkman implement --isolated <idea-dir> [options...]
```

### FR-4: Pass-Through to Inner Command Not Required

The `--type` value must NOT be forwarded to the inner `i2code implement --isolated` command. The inner command runs inside the already-created isolation environment and has no use for the type.

### FR-5: Trunk Mode Incompatibility

`--isolation-type` is incompatible with `--trunk`. If both are specified, raise a `click.UsageError`. This follows the existing pattern in `ImplementOpts.validate_trunk_options()`.

### FR-6: Dry-Run Support

When `--dry-run` is used with `--isolation-type`, the printed mode should be "isolate" (since isolation type implies isolate mode).

## Security Requirements

This feature operates entirely on the local CLI. No network endpoints, APIs, or shared systems are involved.

- **Who can perform this operation:** Any user with local access to the `i2code` CLI.
- **Authorization checks:** None required — the isolarium CLI handles its own authorization for VM/container creation.
- **Constraints:** No secrets or credentials are involved in the `--isolation-type` value; it is a plain type identifier string passed as a command-line argument.

## Non-Functional Requirements

- **Backwards compatibility:** Omitting `--isolation-type` preserves current behavior exactly. No existing command invocations change.
- **Performance:** No impact. The option adds at most two strings to the subprocess argument list.
- **Testability:** All new behavior must be covered by unit tests using the existing fake-based testing pattern (no `@patch` on `IsolateMode` tests).

## Success Metrics

1. `i2code implement --isolation-type <type> <idea-dir>` produces the correct isolarium command with `--type <type>` in global args.
2. `--isolation-type` without `--isolate` activates isolate mode.
3. `--isolation-type` with `--trunk` produces a usage error.
4. All existing tests continue to pass unchanged.

## Epics and User Stories

### Epic: Support Isolation Type Selection

**US-1: Specify isolation type**
As a developer, I want to run `i2code implement --isolation-type docker my-feature` so that isolarium creates a Docker-based isolation environment instead of the default.

**US-2: Isolation type implies isolate mode**
As a developer, I want `--isolation-type` to automatically enable isolation so I don't have to also pass `--isolate`.

**US-3: Combine isolation type with other isolate options**
As a developer, I want to combine `--isolation-type` with flags like `--cleanup`, `--non-interactive`, and `--mock-claude` so I can fully control the isolated run.

**US-4: Error on incompatible mode**
As a developer, I want a clear error if I accidentally combine `--isolation-type` with `--trunk` so I know these are mutually exclusive.

## User-Facing Scenarios

### Scenario 1 (Primary): Specify isolation type for implement

**Given** a valid idea directory `docs/features/my-feature`
**When** the developer runs `i2code implement --isolation-type docker docs/features/my-feature`
**Then** isolate mode is activated (implied by `--isolation-type`)
**And** the isolarium command is: `isolarium --name i2code-my-feature --type docker run --interactive -- i2code --with-sdkman implement --isolated docs/features/my-feature`

### Scenario 2: Isolation type with explicit --isolate

**Given** a valid idea directory
**When** the developer runs `i2code implement --isolate --isolation-type docker docs/features/my-feature`
**Then** the behavior is identical to Scenario 1 (both flags agree on isolate mode)

### Scenario 3: Isolation type with --trunk (error)

**Given** a valid idea directory
**When** the developer runs `i2code implement --trunk --isolation-type docker docs/features/my-feature`
**Then** a `UsageError` is raised: `--trunk cannot be combined with: --isolation-type`

### Scenario 4: Isolation type with non-interactive and cleanup

**Given** a valid idea directory
**When** the developer runs `i2code implement --isolation-type docker --non-interactive --cleanup docs/features/my-feature`
**Then** the isolarium command includes `--type docker` in global args
**And** the inner command includes `--non-interactive` and `--cleanup`

### Scenario 5: No isolation type (backwards compatibility)

**Given** a valid idea directory
**When** the developer runs `i2code implement --isolate docs/features/my-feature`
**Then** the isolarium command does NOT include `--type` (identical to current behavior)

### Scenario 6: Dry run with isolation type

**Given** a valid idea directory
**When** the developer runs `i2code implement --dry-run --isolation-type docker docs/features/my-feature`
**Then** output shows `Mode: isolate` and no subprocess is launched
