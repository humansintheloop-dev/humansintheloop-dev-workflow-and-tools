# Compose Method

## Problem

A long method mixes multiple levels of abstraction — setup details, business logic, and assertions or side effects are interleaved. The reader must mentally parse the entire body to understand the intent. Extracting well-named helper methods lets the composed method read as a narrative at a single level of abstraction.

## Example

### Before

A test method that mixes git repo initialization, file copying, environment setup, Claude invocations, and assertions in a single 60-line body. The reader must track local variables across unrelated concerns to follow the flow.

Reference: `tests/implement/test_scaffolding_task_conflict.py` — original version with inline setup, scaffolding, task execution, and assertions.

### After

The test method reads as a sequence of intention-revealing calls:

1. `_create_test_project(tmp_path)` — returns a `TestProject` dataclass bundling repo, paths, and runners
2. `_run_scaffolding(project)` — invokes Claude for scaffolding
3. Assert CI workflow exists
4. `_run_first_task(project)` — invokes Claude for task execution
5. Assert no duplicate CI files

Each helper operates on a `TestProject` dataclass that bundles related state (repo, idea_dir, tmp_path, command_builder, claude_runner), eliminating long parameter lists.

Reference: `tests/implement/test_scaffolding_task_conflict.py` — refactored version with `TestProject` dataclass and composed helpers.

## Function Ordering

The composed method (the public function or test) appears **first** in the file, followed by the helpers it calls. This mirrors newspaper-style reading — headline first, supporting details below. The reader sees the high-level flow immediately without scrolling past implementation details.

## When to Apply

- A method body exceeds ~20 lines and touches multiple concerns
- You find yourself writing section comments (`# Set up repo`, `# Run scaffolding`) to navigate the body
- Helper methods need 4+ parameters — introduce a dataclass to bundle related state
- A test method mixes setup, action, and assertion at different abstraction levels

## Key Principles

- **One level of abstraction per method.** A method should either do work or delegate, not both. If a line requires understanding internals to follow, extract it.
- **Name methods for intent, not mechanics.** `_create_test_project` reveals purpose; `_init_repo_and_copy_fixtures_and_setup_env` describes steps.
- **Bundle related state into a dataclass.** When multiple helpers need the same group of values, a dataclass eliminates parameter passing and makes the shared context explicit.
- **Public before private, caller before callee.** The composed method appears first in the file. Helpers follow in the order they are called. The reader never has to scroll up.
- **Section comments are an extraction signal.** If you write `# Step 1: ...` and `# Step 2: ...`, each step is a candidate for its own method.
