"""Revise specification via Claude."""

from i2code.claude.permissions import build_allowed_tools_flag
from i2code.implement.claude_runner import ClaudeCodeCommand, ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.template_renderer import render_template


def revise_spec(
    project: IdeaProject,
    claude_runner,
    *,
    repo_root: str | None = None,
) -> ClaudeResult:
    """Revise an existing specification interactively via Claude.

    Validates that both idea and spec files exist, renders the
    revise-spec.md template with the IDEA_DIRECTORY variable, and
    invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        repo_root: Repository root path. When provided, grants file
            permissions via allowed_tools and uses repo root as cwd.

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If the idea or spec file does not exist
    """
    project.validate_idea()
    project.validate_spec()

    prompt = render_template("revise-spec.md", {"IDEA_DIRECTORY": project.directory})

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
