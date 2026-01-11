# Review Project Claude Files for Template Updates

Review the Claude configuration files from a project to identify widely applicable changes that should be incorporated into the template files in config-files/.

## Project Files to Review

- Project CLAUDE.md: $PROJECT_CLAUDE_MD
- Project settings.local.json: $PROJECT_SETTINGS

## Template Files to Update

- Template CLAUDE.md: $CONFIG_CLAUDE_MD
- Template settings.local.json: $CONFIG_SETTINGS

## Instructions

1. Read the project's Claude files (CLAUDE.md and/or .claude/settings.local.json)
2. Read the corresponding template files in config-files/
3. Compare them to identify changes in the project files that are:
   - Generally applicable across different projects (not project-specific)
   - Improvements to best practices, tool selection, or workflow
   - New permissions that would be useful in most projects
   - Refined or clarified guidelines

4. For each potential change:
   - Explain what the change is and why it might be valuable
   - Ask the user if they want to apply this change to the template
   - If confirmed, make the edit to the appropriate config-files/ template

## What to Skip

- Project-specific paths or configurations
- Project-specific build tools or frameworks (unless adding to a general list)
- Permissions that are only relevant to that specific project
- Comments or notes that reference specific project features

## Process

Work through each potential change one at a time, asking for confirmation before making any edits. This ensures the user has full control over what gets incorporated into the templates.
