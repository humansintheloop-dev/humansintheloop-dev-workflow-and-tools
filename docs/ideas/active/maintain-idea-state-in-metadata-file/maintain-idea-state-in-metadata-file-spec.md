# Platform Capability Specification: Maintain Idea State in Metadata File

## Purpose and Context

The i2code idea management system tracks idea lifecycle state (draft, ready, wip, completed, abandoned) by placing each idea's directory under a corresponding state directory (`docs/ideas/{state}/{name}/`). State transitions use `git mv` to move the entire directory, which:

- Creates noisy git history — every file in the idea directory appears renamed on each transition.
- Makes it harder to trace an idea's history — `git log --follow` is required to track files across renames.
- Couples lifecycle state to directory structure, complicating queries and tooling.

This capability replaces directory-based state tracking with a per-idea metadata file. Lifecycle state becomes a field in `<name>-metadata.yaml`, and the 5 state directories collapse into 2: `active/` and `archived/`.

## Consumers

| Consumer | How it uses idea state |
|----------|----------------------|
| `i2code idea state` | Queries and transitions lifecycle state |
| `i2code idea list` | Lists ideas filtered by state |
| `i2code idea brainstorm` | Creates new ideas in draft state |
| `i2code implement` | Reads idea directory, plan file, spec file via `IdeaProject` |
| `write-idea` skill | Creates idea files in the draft state directory |
| Shell completions | Enumerate idea names via `list_ideas()` |

## Capabilities and Behaviors

### C1: Metadata file

Each idea has a metadata file named `<idea-name>-metadata.yaml` inside its directory. Initial schema:

```yaml
state: draft
```

Valid values for `state`: `draft`, `ready`, `wip`, `completed`, `abandoned`.

The file uses YAML for human readability and easy editing. The schema is intentionally minimal — additional fields can be added incrementally without breaking existing metadata files.

### C2: Directory structure

Replace the current 5-directory layout:

```
docs/ideas/
├── draft/<name>/
├── ready/<name>/
├── wip/<name>/
├── completed/<name>/
└── abandoned/<name>/
```

With a 2-directory layout:

```
docs/ideas/
├── active/<name>/
│   ├── <name>-metadata.yaml
│   ├── <name>-idea.md
│   ├── <name>-spec.md
│   ├── <name>-plan.md
│   └── ...
└── archived/<name>/
│   ├── <name>-metadata.yaml
│   └── ...
```

- `active/` contains all ideas the user is actively managing (any lifecycle state).
- `archived/` contains ideas the user has explicitly moved out of their working set.
- Archival is orthogonal to lifecycle state — an archived idea retains its lifecycle state (e.g., an idea can be `completed` and still in `active/` until explicitly archived).

### C3: State transitions

`i2code idea state <name-or-path> <new-state> [--force] [--no-commit]`

Behavior:
1. Resolve the idea by name or path (searching both `active/` and `archived/`).
2. Read current state from the idea's `<name>-metadata.yaml`.
3. Validate the transition using existing rules (unchanged from current implementation):
   - Forward-only progression: draft → ready → wip → completed.
   - No skipping states (e.g., draft → wip is blocked).
   - Transitions to `abandoned` are always allowed from any state.
   - Transitions from draft → ready and ready → wip require a `*-plan.md` file in the idea directory.
   - `--force` bypasses all validation rules.
4. Write the new state value to `<name>-metadata.yaml`.
5. By default, `git add` the metadata file and `git commit` with message: `"Move idea {name} from {old_state} to {new_state}"`.
6. If `--no-commit` is passed, stage the file but do not commit.

No `git mv` is involved — the idea directory stays in place.

### C4: Archive and unarchive

Two new CLI commands:

**`i2code idea archive <name> [--no-commit]`**
1. Resolve the idea in `active/`.
2. `git mv` the idea directory from `docs/ideas/active/<name>/` to `docs/ideas/archived/<name>/`.
3. By default, commit with message: `"Archive idea {name}"`.
4. If `--no-commit`, stage but do not commit.
5. Error if the idea is already in `archived/`.

**`i2code idea unarchive <name> [--no-commit]`**
1. Resolve the idea in `archived/`.
2. `git mv` the idea directory from `docs/ideas/archived/<name>/` to `docs/ideas/active/<name>/`.
3. By default, commit with message: `"Unarchive idea {name}"`.
4. If `--no-commit`, stage but do not commit.
5. Error if the idea is already in `active/`.

### C5: Listing and filtering

`i2code idea list [--state STATE] [--archived] [--all]`

| Flags | Directories scanned | Filter |
|-------|-------------------|--------|
| (none) | `active/` | All active ideas |
| `--state wip` | `active/` | Active ideas where metadata `state` == `wip` |
| `--archived` | `archived/` | All archived ideas |
| `--archived --state completed` | `archived/` | Archived ideas where metadata `state` == `completed` |
| `--all` | `active/` + `archived/` | All ideas |
| `--all --state draft` | `active/` + `archived/` | All ideas where metadata `state` == `draft` |

`--archived` and `--all` are mutually exclusive.

Output format remains the same: aligned columns of name, state, directory.

### C6: Migration command

`i2code idea migrate [--no-commit]`

Migrates from the old directory-based structure to the new metadata-based structure:

1. Detect ideas in old-style directories (`docs/ideas/{draft,ready,wip,completed,abandoned}/<name>/`).
2. If no old-style ideas are found, print a message and exit (idempotent).
3. Create `docs/ideas/active/` and `docs/ideas/archived/` if they don't exist.
4. For each idea found:
   a. Determine the lifecycle state from the current directory path.
   b. `git mv` the idea directory to `docs/ideas/active/<name>/`.
   c. Create `<name>-metadata.yaml` with `state: <detected-state>`.
   d. `git add` the metadata file.
5. Remove empty old state directories.
6. By default, commit all changes in a single commit with message: `"Migrate ideas from directory-based state to metadata files"`.
7. If `--no-commit`, stage all changes but do not commit.

The command is permanent (not a one-off script), so that other adopters of the tool can also migrate.

### C7: Idea creation

When creating a new idea (via `i2code idea brainstorm` or the `write-idea` skill):

1. Create the idea directory under `docs/ideas/active/<name>/`.
2. Create `<name>-metadata.yaml` with `state: draft`.
3. Create the idea file and other initial files as before.

### C8: Idea resolution

The resolver (`resolve_idea`, `list_ideas`) changes from scanning state directories to scanning `active/` and `archived/`:

- **`resolve_idea(name, git_root)`**: Search `active/` and `archived/` for a directory matching `name`. Read `<name>-metadata.yaml` to populate the `state` field of `IdeaInfo`.
- **`list_ideas(git_root)`**: Scan `active/` (and optionally `archived/`) directories. For each idea directory, read the metadata file to get state. Return sorted list of `IdeaInfo`.
- **`state_from_path(path)`**: Replaced by reading the metadata file. For backward compatibility during migration, if the path contains an old-style state directory name, the function can still extract state from the path — but post-migration, all state reads come from metadata files.

The `IdeaInfo` dataclass remains unchanged: `name`, `state`, `directory`.

### C9: IdeaProject changes

Add a `metadata_file` property to `IdeaProject`:

```python
@property
def metadata_file(self) -> str:
    return os.path.join(self.directory, f"{self.name}-metadata.yaml")
```

The existing `state_file` property (for `*-wt-state.json`) remains unchanged — it serves a different purpose (implementation runtime state).

## High-Level APIs, Contracts, and Integration Points

### Metadata file contract

File: `<idea-name>-metadata.yaml`

```yaml
state: <one of: draft, ready, wip, completed, abandoned>
```

- The file is always present in every idea directory (post-migration).
- The file is valid YAML with at minimum a `state` key.
- Unknown keys are preserved (forward compatibility for future fields).
- The file is read via Python's `yaml.safe_load()` and written via `yaml.safe_dump()`.

### CLI contract changes

| Command | Current behavior | New behavior |
|---------|-----------------|--------------|
| `i2code idea state <name>` | Returns state derived from directory path | Returns state read from metadata file |
| `i2code idea state <name> <state>` | `git mv` directory to new state dir + commit | Edit metadata file + commit |
| `i2code idea state <name> <state> --no-commit` | N/A (new flag) | Edit metadata file, stage, no commit |
| `i2code idea list` | Scans 5 state directories | Scans `active/`, reads metadata files |
| `i2code idea list --state X` | Scans single state directory | Scans `active/`, filters by metadata state |
| `i2code idea list --archived` | N/A (new flag) | Scans `archived/` |
| `i2code idea list --all` | N/A (new flag) | Scans `active/` + `archived/` |
| `i2code idea archive <name>` | N/A (new command) | `git mv` active → archived + commit |
| `i2code idea unarchive <name>` | N/A (new command) | `git mv` archived → active + commit |
| `i2code idea migrate` | N/A (new command) | Migrate old structure → new structure |
| `i2code idea brainstorm <dir>` | Creates in `docs/ideas/draft/` | Creates in `docs/ideas/active/` with metadata |

### Internal API changes

| Function/Class | Change |
|---------------|--------|
| `resolver.resolve_idea()` | Scan `active/` + `archived/` instead of 5 state dirs; read metadata file for state |
| `resolver.list_ideas()` | Same scanning change; accept optional `include_archived` parameter |
| `resolver.state_from_path()` | Deprecated; replaced by reading metadata file |
| `resolver.LIFECYCLE_STATES` | Unchanged: `("draft", "ready", "wip", "completed", "abandoned")` |
| `resolver.IdeaInfo` | Unchanged: `name`, `state`, `directory` |
| `transition_rules.validate_transition()` | Unchanged — rules are state-based, not path-based |
| `IdeaProject.metadata_file` | New property returning path to `<name>-metadata.yaml` |
| `IdeaProject` path properties | Unchanged — they derive from `directory`, which is still valid |

## Non-Functional Requirements and SLAs

- **Performance**: `i2code idea list` must scan directories and read metadata files. With ~36 ideas, this adds negligible overhead (36 small YAML file reads). No performance SLA needed.
- **Idempotency**: `i2code idea migrate` is safe to run multiple times — it skips if no old-style directories exist.
- **Atomicity**: State transitions write a single field in a single file. Combined with git commit, this provides atomic state changes.
- **Backward compatibility**: After migration, the old directory structure no longer exists. There is no dual-mode support — the migration is one-way.

## Scenarios and Workflows

### Scenario 1 (Primary): Transition idea state via metadata file

**Precondition**: An idea `my-feature` exists in `docs/ideas/active/my-feature/` with metadata `state: draft` and a plan file `my-feature-plan.md`.

1. User runs: `i2code idea state my-feature ready`
2. System reads `my-feature-metadata.yaml` → current state is `draft`.
3. System validates: draft → ready is allowed, plan file exists.
4. System writes `state: ready` to `my-feature-metadata.yaml`.
5. System runs `git add my-feature-metadata.yaml` and `git commit -m "Move idea my-feature from draft to ready"`.
6. User runs: `i2code idea state my-feature` → output shows `ready`.

**Variant — no commit**: User runs `i2code idea state my-feature ready --no-commit`. Step 5 stages the file but does not commit.

### Scenario 2: Migrate from directory-based state

**Precondition**: Repository has ideas in old-style directories: `docs/ideas/draft/foo/`, `docs/ideas/completed/bar/`.

1. User runs: `i2code idea migrate`
2. System detects 2 ideas in old-style directories.
3. System creates `docs/ideas/active/`.
4. System `git mv`s `docs/ideas/draft/foo/` → `docs/ideas/active/foo/`, creates `foo-metadata.yaml` with `state: draft`.
5. System `git mv`s `docs/ideas/completed/bar/` → `docs/ideas/active/bar/`, creates `bar-metadata.yaml` with `state: completed`.
6. System removes empty old directories.
7. System commits: `"Migrate ideas from directory-based state to metadata files"`.
8. User runs `i2code idea list` → shows `foo (draft)` and `bar (completed)`.

### Scenario 3: Archive and unarchive

**Precondition**: Idea `old-feature` is in `docs/ideas/active/old-feature/` with `state: completed`.

1. User runs: `i2code idea archive old-feature`
2. System `git mv`s directory to `docs/ideas/archived/old-feature/`.
3. System commits: `"Archive idea old-feature"`.
4. User runs: `i2code idea list` → `old-feature` is not shown.
5. User runs: `i2code idea list --archived` → `old-feature` is shown with `state: completed`.
6. User runs: `i2code idea unarchive old-feature` → directory moves back to `active/`.

### Scenario 4: Create new idea with metadata

1. User runs: `i2code idea brainstorm docs/ideas/active/new-idea`
2. System creates `docs/ideas/active/new-idea/` directory.
3. System creates `new-idea-metadata.yaml` with `state: draft`.
4. System creates `new-idea-idea.md` with template text.
5. System opens editor, then invokes Claude for brainstorming.

### Scenario 5: List with filtering

1. User runs: `i2code idea list --state wip` → shows only active ideas with `state: wip`.
2. User runs: `i2code idea list --all --state completed` → shows completed ideas in both `active/` and `archived/`.
3. User runs: `i2code idea list --archived` → shows all archived ideas regardless of lifecycle state.

### Scenario 6: Forced backward transition

1. User runs: `i2code idea state my-feature draft` (current state is `ready`).
2. System rejects: backward transition not allowed.
3. User runs: `i2code idea state my-feature draft --force`.
4. System writes `state: draft` to metadata file and commits.

## Constraints and Assumptions

- **Python YAML library**: The implementation uses `yaml.safe_load()` and `yaml.safe_dump()` from PyYAML (already a project dependency via other paths, or added if not present).
- **No dual-mode**: After migration, only the new structure is supported. The old `state_from_path()` approach is removed.
- **Single repository**: All ideas live in the same git repository. The `docs/ideas/` path is relative to git root.
- **Metadata file required**: Every idea directory must contain a metadata file. If a directory lacks one, `list_ideas()` treats it as an error (logs a warning and skips the idea).
- **No concurrent access**: The tool assumes single-user, single-process access to the repository (consistent with current design).

## Acceptance Criteria

1. **State transitions do not move directories** — `i2code idea state <name> <new-state>` modifies only the metadata file; `git log --name-only` shows only `<name>-metadata.yaml` changed.
2. **Migration is complete** — After running `i2code idea migrate`, no idea directories exist under `docs/ideas/draft/`, `docs/ideas/ready/`, `docs/ideas/wip/`, `docs/ideas/completed/`, or `docs/ideas/abandoned/`. All ideas are under `docs/ideas/active/` with correct metadata files.
3. **Migration is idempotent** — Running `i2code idea migrate` a second time prints a message and exits without error or changes.
4. **Transition rules are preserved** — All existing transition validations (forward-only, plan-file requirements, `--force` override) work identically to the current implementation.
5. **Archive/unarchive round-trips** — Archiving then unarchiving an idea returns it to `active/` with its lifecycle state unchanged.
6. **Listing defaults to active** — `i2code idea list` with no flags shows only ideas in `active/`. Archived ideas require `--archived` or `--all`.
7. **`--no-commit` flag works** — State transitions, archive, unarchive, and migrate all support `--no-commit`, which stages changes without committing.
8. **New ideas get metadata** — `i2code idea brainstorm` creates the metadata file with `state: draft` in the new `active/` directory.
9. **Existing tests pass** — All tests in `tests/idea-cmd/` are updated and pass against the new implementation.
10. **Documentation updated** — `CODEBASE.md` reflects the new directory structure and metadata file convention.
