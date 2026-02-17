# Discussion: Improve Modularity of Implement Package

## Problem Analysis

Review of `tests/implement/` revealed systemic mocking problems rooted in production code design:

- **21 `@patch` decorators** on a single test (`TestGetDefaultBranchWiring`)
- **15 duplicate `MockResult` inline classes** across test files
- **`MagicMock()` without `spec=`** silently accepting any attribute access
- **Three inconsistent mocking styles** (decorators, monkeypatch, pytest-mock)

These are symptoms, not causes. The root cause is that `implement.py` is a 2332-line procedural module with no abstraction boundaries over external systems.

## Key Design Decisions

### GitRepository wraps GitHubClient (not the reverse)

The domain concept is "the repository I'm working in," not "the GitHub API." `GitRepository` is the primary abstraction. It delegates to `GitHubClient` internally for remote operations, but callers don't need to know.

### GitRepository tracks branch and PR state

Currently `slice_branch` and `pr_number` are threaded as parameters through 10+ call sites. These are the repository's working context — it knows what branch it's on and what PR is associated. Making them state on `GitRepository` eliminates parameter threading.

### Execution modes as polymorphism

`implement_cmd` currently branches on 5 modes via if/elif. Extracting `TrunkMode`, `WorktreeMode`, `IsolateMode` as classes with an `execute()` method replaces the conditional with polymorphism and makes each mode independently testable.

### New top-level submodules for reusable infrastructure

- `i2code.idea` — IdeaProject is a domain concept beyond just implement
- `i2code.git` — Git/GitHub access could be reused by other features
- `i2code.claude` — Claude invocation is not implement-specific

### Instructions that would have prevented the current design

Five mechanical rules that catch procedural drift early:

1. Wrap external systems in injectable classes
2. Data that travels together is a class
3. Tests must not use `unittest.mock.patch`
4. No source file may exceed 300 lines
5. State belongs to objects, not loop variables
