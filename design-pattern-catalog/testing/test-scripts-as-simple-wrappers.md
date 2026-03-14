# Test Scripts as Simple Wrappers

## Problem

When integration tests live entirely in shell scripts, the test logic (assertions, data setup, filtering) is written in bash — harder to read, debug, and maintain than equivalent Python. Shell scripts should only handle what shells do best (process orchestration, CLI invocation). The majority of test logic should live in pytest tests where assertions are expressive, fixtures manage setup/teardown, and failures produce clear diagnostics.

## Example

### Before

A 360-line bash script that creates a GitHub repo, pushes commits, creates PRs, posts review comments, resolves threads, and then inlines Python via `python3 -c "..."` blocks to call production filtering methods and assert results. The assertions are buried inside heredoc strings, failures print opaque messages, and cleanup relies on a `trap` handler.

Reference: `test-scripts/test-pr-feedback-filtering.sh` — original version (now removed).

### After

A `@pytest.mark.integration_gh` test class where:

1. A pytest fixture creates the GitHub repo, pushes initial commits, and tears down on exit
2. Each test method sets up its specific scenario (PR, review comments, thread resolution) using `gh` CLI calls
3. Assertions use standard pytest `assert` with descriptive messages
4. Production code is imported and called directly — no `python3 -c` wrappers

Reference: `tests/implement/test_pr_feedback_filtering_integration.py` — `TestPrFeedbackFiltering`

## When to Apply

- Writing a new integration test that needs external infrastructure (GitHub, APIs, databases)
- An existing shell test script contains inline Python or complex assertion logic
- A test script exceeds ~50 lines of non-setup code

## Key Principles

- **Shell for orchestration, Python for logic.** Shell scripts may invoke CLI tools and manage processes, but assertions, data transformation, and production code calls belong in Python.
- **Pytest fixtures replace trap handlers.** `yield`-based fixtures provide deterministic setup/teardown without manual cleanup code.
- **One assertion style.** Mixing `assert` in inline Python with `test` / `[[ ]]` in bash makes failures inconsistent. Pick one — pytest.
- **Test scripts that remain should be thin wrappers.** If a shell script is still needed (e.g., to set environment variables), it should do only that and delegate to `pytest`.
