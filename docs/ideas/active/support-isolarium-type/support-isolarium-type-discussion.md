# Discussion: Support Isolarium Type

## Classification

**User-facing feature (A)** — Adds a new CLI option (`--isolation-type`) to `i2code implement` that users interact with directly.

**Rationale:** This enhances an existing user-facing command with a new option. It does not introduce new architecture, infrastructure, or educational content.

## Codebase Analysis (Derived from Code)

- `i2code implement --isolate` invokes isolarium via `IsolateMode._build_isolarium_command()` in `src/i2code/implement/isolate_mode.py`
- Current command: `isolarium --name i2code-<name> run [--interactive] -- i2code --with-sdkman implement --isolated ...`
- Change follows the established command assembler pattern: `cli.py` → `ImplementOpts` → `ImplementCommand` → `ModeFactory` → `IsolateMode`
- Pass-through option: no validation on our side (isolarium validates `--type`), no default needed (isolarium has its own)
- `--type` does not propagate to the inner `--isolated` command (already inside the VM)

## Questions and Answers

### Q1: Where does `--type` sit in the isolarium CLI?

Is it a global option (before the subcommand, like `--name`), or a subcommand-specific option (after `run`)?

- A. Global: `isolarium --name i2code-foo --type docker run ...`
- B. Subcommand: `isolarium --name i2code-foo run --type docker ...`

**Answer:** A. Global — `isolarium --name i2code-foo --type docker run ...`

### Q2: Should `--isolation-type` require `--isolate`?

If a user passes `--isolation-type docker` without `--isolate`, what should happen?

- A. Error — require `--isolate` when `--isolation-type` is specified
- B. Imply `--isolate` — passing `--isolation-type` automatically enables isolation
- C. Silently ignore — `--isolation-type` has no effect without `--isolate`

**Answer:** B. Imply `--isolate` — passing `--isolation-type` automatically enables isolation. If you're specifying an isolation type, you clearly want isolation.

### Q3: Should `--isolation-type` also apply to `i2code scaffold`?

`scaffold` also has an isolate mode and shares `IsolateMode` via the `ModeFactory`. Should it also get `--isolation-type`?

- A. Yes — add to both `implement` and `scaffold`
- B. No — only `implement` for now

**Answer:** B. Only `implement` for now. Keeps scope focused.
