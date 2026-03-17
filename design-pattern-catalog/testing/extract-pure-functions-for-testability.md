# Extract Pure Functions for Testability

## Problem

Methods that mix coordination logic (reading state from collaborators) with transformation logic (parsing, formatting, computing) are harder to test. The coordination requires constructing the object with all its dependencies, while the transformation is a pure function that takes inputs and returns outputs.

## Example

### Before

A private method on a class that reads from a collaborator and parses in the same step:

`PullRequestReviewProcessor` — `_parse_owner_repo` reads `self._git_repo.origin_url` and parses it. Testing requires constructing the processor with a fake git repo, fake claude runner, fake state, and fake opts — all to test URL string parsing.

Reference: `src/i2code/implement/pull_request_review_processor.py` — `_parse_owner_repo`

### After

A module-level pure function handles the transformation. The method on the class becomes a one-line delegation that passes the collaborator's value to the pure function.

- `parse_owner_repo(url: str) -> tuple[str, str]` — pure function, takes a string, returns a tuple. Testable with a single function call.
- `_parse_owner_repo(self)` — one-line coordinator: `return parse_owner_repo(self._git_repo.origin_url)`

Testing the pure function requires no object construction — just `assert parse_owner_repo("git@github.com:owner/repo.git") == ("owner", "repo")`.

## Testing Strategies

### Direct unit test of the pure function

**What is tested:** `parse_owner_repo` — the extracted module-level function.

Tests call the function directly with various URL formats and assert the returned tuple. No fakes, no setup.

Reference: `tests/implement/test_pull_request_review_processor.py` — `TestParseOwnerRepo`

## When to Apply

- A method mixes `self.collaborator.value` reads with non-trivial transformation logic
- Testing a method requires constructing an object with multiple dependencies, but the logic under test doesn't use those dependencies
- The same parsing/formatting logic could be reused elsewhere

## Key Principles

- **Separate coordination from computation.** Coordination reads state and delegates. Computation takes values and returns values. Keep them in different functions.
- **Pure functions are trivially testable.** No mocks, no fakes, no setup — just input and expected output.
- **One-line delegation is fine.** The coordinating method can be a single line that passes collaborator state to the pure function. It doesn't need its own test.
