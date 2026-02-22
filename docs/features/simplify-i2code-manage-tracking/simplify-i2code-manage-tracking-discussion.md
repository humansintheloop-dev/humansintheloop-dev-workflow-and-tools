# Discussion: Simplify i2code manage-tracking

## Context

The current command is `i2code manage-tracking` with two separate flags:
- `--migrate` — moves `.claude/{issues,sessions}` to `.hitl/`, updates `.gitignore`
- `--link DIR` — symlinks `.hitl/{issues,sessions}` to an external directory

Implementation lives in:
- `src/i2code/tracking/cli.py` (Click command)
- `src/i2code/tracking/manage.py` (TrackingManager class)
- Registered in `src/i2code/cli.py`

The proposal is to rename to `i2code tracking setup`.

## Questions and Answers

### Q1: Command behavior — combine migrate + link into one operation?

Currently the user must explicitly pass `--migrate` and/or `--link DIR`. The idea description reads as though `i2code tracking setup` should always perform migration (creating `.hitl/`, migrating legacy files, updating `.gitignore`) as its default behavior, with `--link DIR` remaining optional.

Is that correct — `setup` always migrates, and `--link` is the only optional flag?

**A1:** Yes. `i2code tracking setup` always performs migration. `--link DIR` is the only optional flag.

### Q2: Command group — future subcommands under `tracking`?

Renaming from `i2code manage-tracking` to `i2code tracking setup` makes `tracking` a Click command group with `setup` as a subcommand. This structure anticipates future subcommands (e.g., `i2code tracking status`, `i2code tracking reset`).

What is the intent behind making `tracking` a command group?

A. Cleaner namespace only — no other subcommands planned right now
B. Future subcommands planned (e.g., `tracking status`, `tracking reset`) — but out of scope for this work
C. Future subcommands planned and some should be included in this scope

**A2:** A — cleaner namespace only. No other subcommands planned.

### Q3: Should `--dry-run` be preserved?

A. Keep `--dry-run` as-is
B. Drop `--dry-run` — not needed
C. Keep `--dry-run` but make it the default (require `--execute` or `--force` to actually run)

**A3:** A — keep `--dry-run` as-is.

### Q4: Scope of changes — what does this work include?

Given that the `TrackingManager` implementation in `manage.py` already handles all the behaviors described in the idea, this work appears to be purely a CLI restructuring:

1. Rename the Click command from `manage-tracking` to `tracking setup` (command group + subcommand)
2. Remove the `--migrate` flag — migration always runs
3. Keep `--link DIR` and `--dry-run` as optional flags
4. Update registration in `cli.py`
5. Update any tests

Is there any behavioral change to the underlying `TrackingManager` logic, or is this purely a CLI rename/simplification?

A. CLI-only — no changes to `TrackingManager` logic in `manage.py`
B. There are also behavioral changes to the migration/link logic (please describe)

**A4:** There is one new behavior: consolidating subdirectory `.hitl/` directories (new format already in subdirs) to the top-level `.hitl/` and replacing them with symlinks. Currently `_migrate_subdirectories` only handles legacy `.claude/` dirs in subdirectories — it explicitly skips `.hitl` dirs during the walk (`manage.py:313`).

### Q5: Consolidating subdirectory `.hitl/` directories

To confirm the expected behavior for subdirectory `.hitl/` real directories:

1. Merge contents of `subdir/.hitl/{sessions,issues}` into top-level `.hitl/{sessions,issues}`
2. Replace `subdir/.hitl/{sessions,issues}` with relative symlinks to the top-level

This matches the existing pattern used for legacy `.claude/` subdirectories. Should the behavior be identical (merge + symlink), or is there any difference?

A. Same behavior as legacy `.claude/` subdirectory migration (merge contents + replace with symlinks)
B. Different behavior (please describe)

**A5:** A — same behavior. Merge contents into top-level `.hitl/` and replace with relative symlinks.

### Q6: Backward compatibility for `manage-tracking`

Since this is a rename from `i2code manage-tracking` to `i2code tracking setup`, should the old command name remain as a deprecated alias, or be removed outright?

A. Remove `manage-tracking` entirely — clean break
B. Keep `manage-tracking` as a deprecated alias that prints a warning and delegates to `tracking setup`
C. Keep `manage-tracking` as a silent alias (no deprecation warning)

**A6:** A — remove `manage-tracking` entirely.

**Note:** References to `manage-tracking` exist in these files that will need updating:
- `docs/i2code-cli/manage-tracking.adoc`
- `docs/i2code-cli/i2code-cli.adoc`
- `README.adoc`
- `src/i2code/cli.py`
- `src/i2code/tracking/cli.py`

### Q7: Idempotency

The current implementation is mostly idempotent (re-running reports "Nothing to migrate", "already linked", etc.). With `setup` always running migration, should it be fully idempotent — safe to run repeatedly with no errors and no unintended side effects?

A. Yes, fully idempotent — running `tracking setup` on an already-set-up project is a no-op with informational output
B. It should warn or error if already set up
C. Don't care — current behavior is fine as-is

**A7:** A — fully idempotent.

## Summary of Scope

**CLI changes:**
- Rename `i2code manage-tracking` → `i2code tracking setup` (command group + subcommand)
- Remove `--migrate` flag — migration always runs as default behavior
- Keep `--link DIR` (optional) and `--dry-run` (optional)
- Remove old `manage-tracking` command entirely — no deprecated alias

**New behavior:**
- Consolidate subdirectory `.hitl/` real directories (not just legacy `.claude/`) into top-level `.hitl/` with relative symlinks — same merge+symlink pattern as existing legacy `.claude/` subdirectory handling

**Properties:**
- Fully idempotent — safe to run repeatedly

**Files requiring updates:**
- `src/i2code/tracking/cli.py` — rewrite as command group with `setup` subcommand
- `src/i2code/tracking/manage.py` — extend `_migrate_subdirectories` to handle `.hitl/` subdirs
- `src/i2code/cli.py` — update registration
- `docs/i2code-cli/manage-tracking.adoc` — rename/update
- `docs/i2code-cli/i2code-cli.adoc` — update references
- `README.adoc` — update references
- Tests — update for new command structure

## Classification

**Type: A — User-facing feature**

**Rationale:** This is a CLI UX improvement that simplifies the user-facing interface. It renames a command, removes a redundant flag, and extends migration behavior — all directly affecting how users interact with the tool.

### Q8: Final check

Are there any additional requirements or concerns before we move to the next step (creating the detailed specification)?
