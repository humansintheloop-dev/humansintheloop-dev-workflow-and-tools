# Update Project CLAUDE.md from Template

Reconcile the project's CLAUDE.md with the current template version, preserving
project-specific content while merging in template improvements.

## Files

- Project CLAUDE.md: $PROJECT_CLAUDE_MD
- Template CLAUDE.md: $CONFIG_CLAUDE_MD
- Project directory: $PROJECT_DIR

## Sync Context

- First sync: $IS_FIRST_SYNC
- Previous template revision: $PREVIOUS_SHA
- Current template revision: $CURRENT_SHA

## Template Content / Diff

$CONFIG_DIFF

## Instructions

1. Read the project's CLAUDE.md and the current template CLAUDE.md.
2. If this is the first sync, treat the template content above as the authoritative
   reference and identify each section that should be merged into the project file.
   Otherwise, walk through the diff above and identify each substantive change.
3. For each candidate change, in order:
   - Explain in plain language what the change is and why it matters.
   - Determine whether the change is generally applicable or whether it conflicts
     with project-specific customizations already present in the project's CLAUDE.md.
   - Ask the user whether to apply the change, with a clear description of how it
     would be applied (insert, modify, replace section).
   - If the user confirms, edit the project's CLAUDE.md accordingly.
4. Preserve any project-specific sections, headings, and prose that are not part of
   the template. Do not delete project-only content without explicit confirmation.
5. When merging new template sections, place them at a position that mirrors the
   template's structure unless the user specifies otherwise.

## What to Consider

- Template changes are generally applicable improvements.
- Some changes may conflict with project-specific customizations.
- Preserve any project-specific additions that aren't in the template.
- Merge headings and prose carefully — markdown structure matters.

## Process

Work through one candidate change at a time, pausing for confirmation before
making any edit. This ensures project-specific customizations are preserved
while still incorporating template improvements.
