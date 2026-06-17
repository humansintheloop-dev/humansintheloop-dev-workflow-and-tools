"""Revise implementation plan via Claude interactively."""

from i2code.claude.permissions import build_allowed_tools_flag
from i2code.implement.claude_runner import ClaudeCodeCommand, ClaudeResult
from i2code.implement.idea_project import IdeaProject


def revise_plan(project: IdeaProject, claude_runner, template_renderer, *, repo_root: str | None = None) -> ClaudeResult:
    """Revise an existing implementation plan interactively via Claude.

    Validates that idea, spec, and plan files exist, renders the
    revise-plan.md template, and invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable to render prompt templates
        repo_root: Optional repo root for allowed_tools and cwd

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If the idea, spec, or plan file does not exist
    """
    project.validate_idea()
    project.validate_spec()
    project.validate_plan()

    prompt = template_renderer("revise-plan.md", {
        "IDEA_FILE": project.idea_file,
        "SPEC_FILE": project.spec_file,
        "PLAN_WITHOUT_STORIES_FILE": project.plan_file,
    })

    allowed_tools = (
        build_allowed_tools_flag(repo_root, project.directory)
        if repo_root is not None else None
    )
    cwd = repo_root if repo_root is not None else project.directory

    return claude_runner.execute(
        ClaudeCodeCommand(
            cwd=cwd,
            prompt=prompt,
            interactive=True,
            allowed_tools=allowed_tools,
        ),
    )
