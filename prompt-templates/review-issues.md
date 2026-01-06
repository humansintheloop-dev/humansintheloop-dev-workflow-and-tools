# Review Active Issues

Review each active issue and incorporate suggested improvements into this project's skills and prompts.

## Active Issues to Review

$ACTIVE_ISSUES

## Instructions

For each issue file:

1. **Read the issue** to understand the problem and suggested improvement

2. **Evaluate relevance**: Does it suggest an improvement to a skill, prompt or config-file in this project?
   - If YES: add `type: hitl` to the frontmatter and proceed to step 3
   - If NO: add `type: unknown` to the frontmatter and skip to the next issue

3. **Incorporate the change**:
   - Find the relevant skill file (in `skills/`) or prompt template (in `prompt-templates/`) or CLAUDE.md (in `config-files/`)
   - Apply the suggested improvement
   - Use your judgment to adapt the suggestion if needed
   - In particular, carefully consider whether the change should be applied to CLAUDE.md, a new or existing skill, or prompt template

4. **Commit the change immediately**:
   - Use the `idea-to-code:commit-guidelines` skill for the commit message format
   - Commit the changes with a message describing the improvement
   - **IMPORTANT**: Commit EACH change before moving to the next issue
   - Do NOT batch multiple changes into a single commit
   - Each commit should represent one logical improvement from one issue

5. **Update the issue**:
   - Change `status: active` to `status: resolved` in the frontmatter
   - Fill in the `## Resolution` section describing what was done

6. **Move the issue** to the resolved directory:
   - Move from `.../issues/active/` to `.../issues/resolved/`

## Important

- Only modify issues that suggest improvements to THIS project (genai-development-workflow)
- If an issue is unclear or the suggestion doesn't apply, mark it with `type: unknown`
- Issues marked `type: unknown` will be skipped in future runs
- Summarize what you did for each issue reviewed
