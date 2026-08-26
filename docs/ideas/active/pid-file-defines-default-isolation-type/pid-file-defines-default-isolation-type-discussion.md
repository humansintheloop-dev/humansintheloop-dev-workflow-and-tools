# pid.yaml defines default isolation type - Discussion

## Classification

**Type:** A. User-facing feature

**Rationale:** This idea streamlines the existing isolation-type selection workflow by adding project-level defaults via `pid.yaml`. It directly improves the CLI UX for users working on projects that consistently use one isolation type, eliminating repetitive per-idea configuration.

## Codebase Analysis (pre-discussion)

- `i2code implement` already supports `--isolation-type TYPE` (nono/container/vm) via CLI flag
- `i2code go` prompts for isolation type with choices `["None", "Nono", "Container", "VM"]` and stores the selection per-idea in `{name}-implement-config.yaml`
- No project-level config file exists yet — each idea gets its own config
- `pid.yaml` would introduce the first project-level configuration mechanism

## Questions and Answers

