# i2code completion — Specification

## Purpose and Background

The `i2code` CLI is built with Click 8.x, which provides built-in shell completion for bash, zsh, and fish. However, activating this completion requires knowing an undocumented convention: setting the `_I2CODE_COMPLETE` environment variable (e.g., `_I2CODE_COMPLETE=zsh_source i2code`). This feature adds a discoverable `i2code completion` command that wraps this mechanism.

## Target Users

- **i2code CLI users** — developers who use the `i2code` tool and want tab-completion for its commands, subcommands, and options.

## Problem Statement

The i2code CLI has 10 subcommand groups with `plan` alone having 20+ subcommands. Without shell completion, users must memorize or look up command names. Click provides completion out of the box, but the activation mechanism is hidden behind an environment variable convention that users are unlikely to discover.

## Goals

1. Make shell completion discoverable via a first-class CLI command.
2. Support all shells that Click supports: bash, zsh, and fish.
3. Keep the implementation minimal — delegate to Click's built-in completion mechanism.

## In Scope

- `i2code completion` command that prints brief usage help with installation instructions
- `i2code completion <shell>` that outputs the completion script to stdout
- Shell argument validated via `click.Choice(["bash", "zsh", "fish"])`
- Completion covers command names, option names, and `click.Choice`-typed arguments (Click's built-in behavior)

## Out of Scope

- Custom completion callbacks for dynamic arguments (e.g., plan file paths, thread names) — future idea
- Auto-install to shell config files
- Shells not supported by Click (e.g., PowerShell)

## Functional Requirements

### FR-1: Completion script generation

When invoked as `i2code completion <shell>`, the command outputs the shell-specific completion script to stdout. The script is equivalent to what Click generates via the `_I2CODE_COMPLETE=<shell>_source i2code` mechanism.

Supported `<shell>` values: `bash`, `zsh`, `fish`.

### FR-2: Usage help with no arguments

When invoked as `i2code completion` with no shell argument, the command prints a brief usage message including:
- The command syntax
- Supported shell types
- Installation instructions showing how to eval or save the output

Example output:
```
Generate shell completion scripts.

Supported shells: bash, zsh, fish

To install, add to your shell config:
  eval "$(i2code completion zsh)"
```

### FR-3: Invalid shell argument handling

When invoked with an unsupported shell argument (e.g., `i2code completion powershell`), Click's `click.Choice` validation produces an error message listing valid choices and exits with a non-zero status code.

## Security Requirements

No security requirements. This command generates static shell scripts from Click's built-in completion mechanism. It does not access files, network resources, or user data. There are no authorization checks needed.

## Non-Functional Requirements

### UX
- The command should follow the same pattern as `gh completion` — output to stdout, user handles installation.
- Help text should be concise and actionable.

### Performance
- No performance concerns. Script generation is instantaneous.

### Reliability
- The generated completion scripts must be valid for each target shell.

## Success Metrics

- Users can set up shell completion for i2code using only `i2code completion --help` as a guide.
- Tab completion works for all registered commands and options after installation.

## Epics and User Stories

### Epic: Shell Completion Command

**US-1: Generate completion script**
As an i2code user, I want to run `i2code completion zsh` so that I get a completion script I can install in my shell.

**US-2: Discover how to install completions**
As an i2code user, I want to run `i2code completion` with no arguments so that I see instructions for installing shell completions.

**US-3: Get feedback on invalid shell**
As an i2code user, if I run `i2code completion powershell`, I want a clear error telling me which shells are supported.

## User-Facing Scenarios

### Scenario 1: Generate and install zsh completions (primary end-to-end scenario)

1. User runs `i2code completion zsh`.
2. Command outputs the zsh completion script to stdout.
3. User adds `eval "$(i2code completion zsh)"` to their `.zshrc`.
4. After reloading the shell, `i2code pl<TAB>` completes to `i2code plan`.

### Scenario 2: Discover completion setup

1. User runs `i2code completion` with no arguments.
2. Command prints usage help with supported shells and installation instructions.
3. User follows the instructions to set up completion for their shell.

### Scenario 3: Invalid shell argument

1. User runs `i2code completion powershell`.
2. Command prints an error indicating `powershell` is not a valid choice, listing `bash`, `zsh`, and `fish`.
3. Command exits with non-zero status.

### Scenario 4: Save completion to file (bash)

1. User runs `i2code completion bash > ~/.local/share/bash-completion/completions/i2code`.
2. The completion script is written to the file.
3. On next shell session, bash loads the completion automatically.
