# Update Project settings.local.json from Template

Reconcile the project's `.claude/settings.local.json` with the current template
version, merging new permission entries while preserving project-specific entries.

## Files

- Project settings: $PROJECT_SETTINGS
- Template settings: $CONFIG_SETTINGS
- Project directory: $PROJECT_DIR

## Sync Context

- First sync: $IS_FIRST_SYNC
- Previous template revision: $PREVIOUS_SHA
- Current template revision: $CURRENT_SHA

## Template Content / Diff

$CONFIG_DIFF

## Instructions

1. Read the project's `settings.local.json` and the current template
   `settings.local.json`.
2. If this is the first sync, treat the template content above as the authoritative
   reference and identify each entry under `permissions.allow`, `permissions.deny`,
   and `permissions.ask` that should be merged into the project file. Otherwise,
   walk through the diff above and identify each substantive change to the
   permission arrays.
3. For each candidate change, in order:
   - Explain in plain language which permission entry is being added, removed, or
     modified and why it matters.
   - Determine whether the change is generally applicable or whether it conflicts
     with project-specific permission entries already present in the project's
     `settings.local.json`.
   - Ask the user whether to apply the change, with a clear description of how it
     would be applied (insert into `allow`/`deny`/`ask`, remove, or replace).
   - If the user confirms, edit the project's `settings.local.json` accordingly,
     preserving valid JSON formatting and existing key order.
4. Preserve any project-specific permission entries that are not part of the
   template. Do not delete project-only entries without explicit confirmation.
5. When merging new permission entries, append them to the appropriate array
   (`allow`, `deny`, or `ask`) unless the user specifies otherwise.

## What to Consider

- Template changes are generally applicable improvements to the project's
  permission set.
- Some template entries may overlap with project-specific entries — confirm
  before consolidating.
- Preserve any project-specific permission entries that aren't in the template.
- Maintain valid JSON: arrays of strings under `permissions.allow`,
  `permissions.deny`, and `permissions.ask`.

## Process

Work through one candidate change at a time, pausing for confirmation before
making any edit. This ensures project-specific permissions are preserved while
still incorporating template improvements.
