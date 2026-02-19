# Update Project Claude Files from Templates

Update the project's Claude configuration files with changes from the template files in config-files/.

## Project Files to Update

- Project CLAUDE.md: $PROJECT_CLAUDE_MD
- Project settings.local.json: $PROJECT_SETTINGS

## Template Files (Source of Changes)

- Template CLAUDE.md: $CONFIG_CLAUDE_MD
- Template settings.local.json: $CONFIG_SETTINGS

## Change Tracking

- Previous template SHA: $PREVIOUS_SHA
- Current template SHA: $CURRENT_SHA

## Template Changes Since Last Update

$CONFIG_DIFF

## Instructions

1. Read the project's Claude files (CLAUDE.md and .claude/settings.local.json)
2. Read the current template files in config-files/
3. Review the template changes shown above (diff since last update)
4. For each change in the templates:
   - Determine if the change should be applied to the project
   - Explain what the change is
   - Ask the user if they want to apply this change to the project files
   - If confirmed, make the edit to the appropriate project file

5. After all changes are processed, update the SHA tracking comment at the end of the project's CLAUDE.md:
   ```
   <!-- claude-config-files-sha: $CURRENT_SHA -->
   ```

## What to Consider

- Template changes are generally applicable improvements
- Some changes may conflict with project-specific customizations
- Preserve any project-specific additions that aren't in the template
- Merge new permissions from settings.local.json, keeping project-specific ones

## Process

Work through each template change one at a time, asking for confirmation before making any edits. This ensures project-specific customizations are preserved while incorporating template improvements.
