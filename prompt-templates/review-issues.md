# Review Active Issues

Review each active issue and incorporate suggested improvements into this project's skills and prompts.

## Active Issues to Review

$ACTIVE_ISSUES

## Instructions

For each issue file:

1. **Read the issue** to understand the problem and suggested improvement

2. **Evaluate relevance**: Does it suggest an improvement to a skill, prompt or config-file in this project?
   - If YES: proceed to step 3
   - If NO: skip this issue (leave it active for manual review)

3. **Incorporate the change**:
   - Find the relevant skill file (in `skills/`) or prompt template (in `prompt-templates/`)
   - Apply the suggested improvement
   - Use your judgment to adapt the suggestion if needed

4. **Commit the change**:
   - Use the `idea-to-code:commit-guidelines` skill for the commit message format
   - Commit the changes with a message describing the improvement

5. **Update the issue**:
   - Change `status: active` to `status: resolved` in the frontmatter
   - Fill in the `## Resolution` section describing what was done

6. **Move the issue** to the resolved directory:
   - Move from `.../issues/active/` to `.../issues/resolved/`

## Important

- Only modify issues that suggest improvements to THIS project (genai-development-workflow)
- If an issue is unclear or the suggestion doesn't apply, leave it as active
- Summarize what you did for each issue reviewed
