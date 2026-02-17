# Idea: Improve Modularity of Implement Package

Extract the 2332-line procedural `implement.py` into cohesive classes with injectable dependencies, eliminating the need for `unittest.mock.patch` in tests.

## Motivation

The current `src/i2code/implement/implement.py` is a God module containing 60+ free functions that directly call `subprocess.run`, GitPython `Repo`, and other external systems. Tests require 6-21 `@patch` decorators per test method, are coupled to import paths, and use `MagicMock` without `spec=`.

## Desired Outcome

- Production code organized into small, cohesive classes with injected dependencies
- Tests use fake collaborators instead of `unittest.mock.patch`
- No source file exceeds 300 lines
- Reusable infrastructure extracted into `i2code.git`, `i2code.claude`, and `i2code.idea` submodules
