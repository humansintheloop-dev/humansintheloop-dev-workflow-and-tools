# Specification: Improve Modularity of Implement Package

## Scope

Refactor `src/i2code/implement/` from procedural transaction-script style into object-oriented design with injectable dependencies.

## Design Rules

1. Every external system (subprocess, filesystem, network) must be accessed through a class passed as a constructor argument
2. If two or more values are passed together to three or more functions, they become a class
3. Tests must not use `unittest.mock.patch` — use dependency injection and fake collaborators
4. No source file may exceed 300 lines
5. Mutable state tracked in loop variables that is passed to called functions belongs in a class

## Target Structure

| Class | Module | Responsibility |
|-------|--------|----------------|
| `IdeaProject` | `i2code.idea` | Value object: directory + name + plan file path. Owns validation. |
| `WorkflowState` | `i2code.implement` | State persistence (slice_number, processed IDs). Owns load/save. |
| `GitHubClient` | `i2code.git` | Wraps all `gh` CLI calls. Injected into GitRepository. |
| `GitRepository` | `i2code.git` | Wraps Git operations. Tracks current branch and PR number. |
| `ClaudeRunner` | `i2code.claude` | Wraps Claude invocation. Strategy: real vs mock script. |
| `CommandBuilder` | `i2code.claude` | Builds all Claude command lists. |
| `TrunkMode` | `i2code.implement` | Execution mode: tasks on current branch. |
| `WorktreeMode` | `i2code.implement` | Execution mode: worktree + PR + CI. |
| `IsolateMode` | `i2code.implement` | Execution mode: delegates to isolarium VM. |

## Constraints

- Behavior must be preserved — this is a refactoring, not a feature change
- Each thread is independently committable with all tests passing
- Integration tests (`test_git_infrastructure.py`, `test_project_setup_integration.py`, `test_task_execution_integration.py`) are left unchanged
