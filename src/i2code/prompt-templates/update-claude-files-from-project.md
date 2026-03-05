# Review Project Claude Files for Template Updates

Review the Claude configuration files from a project to identify widely applicable changes that should be incorporated into the template files in config-files/.

## Project Files to Review

- Project CLAUDE.md: $PROJECT_CLAUDE_MD
- Project settings.local.json: $PROJECT_SETTINGS

## Template Files to Update

- Template CLAUDE.md: $CONFIG_CLAUDE_MD
- Template settings.local.json: $CONFIG_SETTINGS

## Workflow

1. Read all 4 files in parallel — project and template versions of each config file
2. Identify all differences between the project files and the template files
3. Categorize each change as generally applicable or project-specific
4. Ask about generally applicable changes first, one at a time using `AskUserQuestion`, applying each immediately after approval
5. Then ask about project-specific changes, one at a time using `AskUserQuestion`, applying each immediately after approval
6. Verify final state by reading the updated template files

Every difference is presented to the user — nothing is silently skipped. The categorization determines the order of presentation, not whether a change is shown.

## What Counts as Generally Applicable

- Improvements to best practices, tool selection, or workflow
- New permissions that would be useful in most projects
- Refined or clarified guidelines

## What Counts as Project-Specific

- Project-specific paths or configurations
- Project-specific build tools or frameworks (unless adding to a general list)
- Permissions that are only relevant to that specific project
- Comments or notes that reference specific project features
