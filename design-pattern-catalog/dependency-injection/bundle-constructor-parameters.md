# Bundle Constructor Parameters

## Problem

A code health tool flags a constructor with too many parameters (e.g., 5 when the threshold is 4). The tempting fix is to instantiate a dependency inside the constructor, reducing the parameter count. This breaks dependency injection: the class becomes coupled to a concrete collaborator, and tests can no longer substitute fakes without patching.

## Structure

Two legitimate strategies for reducing constructor parameters while preserving dependency injection:

| Strategy | When to use | Effect |
|----------|------------|--------|
| Bundle related parameters into a dataclass | Two or more parameters travel together and are used together | Fewer constructor args, cohesive grouping |
| Extract a new collaborator class | A consumer only needs part of the interface | Each consumer receives a focused collaborator |

### Anti-pattern: inlining instantiation

Moving `self._collaborator = ConcreteClass(arg1, arg2)` into `__init__` couples the class to the concrete type. Tests must now patch the import or accept the real implementation. This trades a clean design problem (too many args) for a worse one (untestable coupling).

### Reference implementation

**Bundle strategy:**

- `Workspace` in `src/i2code/implement/workspace.py` — bundles `git_repo` and `project` into a single parameter
- `TrunkMode` in `src/i2code/implement/trunk_mode.py` — accepts `Workspace` instead of separate `git_repo` and `project`
- `ModeFactory.make_trunk_mode` in `src/i2code/implement/mode_factory.py` — constructs `Workspace` and passes it to `TrunkMode`

**Extract strategy:**

- `ScaffoldingCreator` in `src/i2code/implement/project_scaffolding.py` — extracted from `ProjectScaffolder` so that `ScaffoldCommand` receives only the collaborator it needs
- `ProjectScaffolder` in `src/i2code/implement/project_scaffolding.py` — receives `ScaffoldingCreator` instead of `command_builder` + `claude_runner`

## When to Apply

- A code health tool flags excess constructor arguments
- Two or more parameters are always passed together across call sites
- A consumer only needs a subset of the class's interface

## Key Principles

- **Never reduce parameter count by inlining instantiation.** The parameter count drops, but testability and flexibility drop further.
- **Bundle parameters that travel together.** If two args always appear as a pair in constructors and method calls, they belong in a dataclass.
- **Extract when a consumer only needs part of the interface.** If a caller uses one method, give it a focused collaborator instead of the full object.
- **The factory owns construction, the class owns behavior.** `ModeFactory` and `command_assembler` build the dependency graph; domain classes receive finished collaborators.
