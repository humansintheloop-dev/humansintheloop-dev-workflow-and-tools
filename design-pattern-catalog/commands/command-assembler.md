# Command + Assembler Pattern

## Problem

CLI handlers accumulate dependency construction alongside argument parsing, making them hard to test. Tests end up patching internal constructors to control a single object they actually care about.

## Structure

Four distinct responsibilities, each in its own file:

| Key Element | File | Responsibility |
|-------------|------|---------------|
| Click command function | `cli.py` | Parses args into opts, calls `assemble_command()`, calls `execute()` |
| Opts dataclass | `*_opts.py` | Typed boundary between CLI and domain |
| `assemble_*()` functions | `command_assembler.py` | Receives opts, wires dependencies, returns command object |
| Command class | `*_command.py` | Constructor receives opts and dependencies, `execute()` runs business logic |

### Reference implementation

- `implement_cmd()`, `scaffold_cmd()` in `src/i2code/implement/cli.py` — creates opts, calls `assemble_command()`, calls `execute()`
- `ImplementOpts` in `src/i2code/implement/implement_opts.py`, `ScaffoldOpts` in `src/i2code/implement/scaffold_opts.py`
- `assemble_implement()`, `assemble_scaffold()`, `assemble_command()` in `src/i2code/implement/command_assembler.py` — wires dependencies, returns command; `assemble_command()` resolves factory from `ctx.obj["command_factory"]` or falls back to the default
- `ImplementCommand` in `src/i2code/implement/implement_command.py`, `ScaffoldCommand` in `src/i2code/implement/scaffold_command.py`

## Testing Strategies

### Test command class

**What is tested:** The behavior of the command class (`ImplementCommand`, `ScaffoldCommand`).

Construct the command with fakes/mocks — no Click, no assembler involved. The test knows about the command and its constructor arguments, not the dependency graph behind the assembler.

- Helper: `tests/implement/test_implement_command.py` — `_make_command()`
- Example: `tests/implement/test_implement_command.py` — `test_setup_only_does_not_create_pr`

### Test Click command function

**What is tested:** The Click command function (`implement_cmd`, `scaffold_cmd`) — that CLI flags are correctly packed into opts, passed to the factory, and `execute()` is called on the resulting command.

Inject a `command_factory` via `ctx.obj`. No patching needed.

- Example: `tests/implement/test_implement_command.py` — `test_uses_command_factory_and_forwards_opts`
- Example: `tests/implement/test_project_setup.py` — `TestScaffoldCmd`

### Anti-pattern: patching the dependency graph

Avoid patching internal constructors (`Repo`, `GitHubClient`, `GitRepository`, etc.) inside the assembler to control behavior of the command under test. This couples tests to wiring details they don't care about.

## When to Apply

- The command handler has more than trivial dependency construction
- Tests need to control collaborators to verify behavior
- Multiple tests exist for different behaviors of the same command

## Key Principles

- **Assemblers build, callers execute.** The assembler returns an object; it never calls `execute`.
- **Test the command, not the wiring.** Construct the command directly with fakes. Skip Click and the assembler entirely.
- **CLI tests verify flag forwarding only.** Use `command_factory` in `ctx.obj` to verify that Click options reach the command as typed opts.
- **Context overrides, not patches.** `assemble_command()` checks `ctx.obj["command_factory"]` before falling back to the default assembler — tests inject via Click's public API.
