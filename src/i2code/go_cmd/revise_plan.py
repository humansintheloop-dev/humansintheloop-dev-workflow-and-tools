"""Revise implementation plan via Claude interactively."""

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject


def revise_plan(project: IdeaProject, claude_runner, template_renderer) -> ClaudeResult:
    """Revise an existing implementation plan interactively via Claude.

    Validates that idea, spec, and plan files exist, renders the
    revise-plan.md template, and invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable to render prompt templates

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If the idea, spec, or plan file does not exist
    """
    project.validate_idea()
    project.validate_spec()
    project.validate_plan()

    rendered_prompt = template_renderer("revise-plan.md", {
        "IDEA_FILE": project.idea_file,
        "SPEC_FILE": project.spec_file,
        "PLAN_WITHOUT_STORIES_FILE": project.plan_file,
    })

    cmd = ["claude", rendered_prompt]
    return claude_runner.run_interactive(cmd, cwd=project.directory)
