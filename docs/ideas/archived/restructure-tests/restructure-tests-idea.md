# Idea: Restructure Unit Tests by Module

Reorganize unit tests in `tests/implement/` so each test file maps to exactly one production module in `src/i2code/implement/`, eliminating duplication and centralizing coverage.

## Problem

Tests are spread across kitchen-sink files (`test_github_pr.py`, `test_claude_invocation.py`) and have significant duplication between files (~30 duplicate tests). This makes it hard to find all tests for a given module and creates maintenance burden.

## Outcome

One `test_<module>.py` per production module. ~30 duplicate tests eliminated, ~50 tests moved to correct module files.
