"""Create specification from an idea via Claude."""

from i2code.claude.permissions import build_allowed_tools_flag
from i2code.implement.claude_runner import ClaudeCodeCommand, ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.session_manager import read_session_id
from i2code.template_renderer import render_template


def create_spec(
    project: IdeaProject,
    claude_runner,
    *,
    repo_root: str | None = None,
) -> ClaudeResult:
    """Generate a specification from an idea file using Claude.

    Validates the idea file exists, renders the create-spec.md template
    with IDEA_FILE and DISCUSSION_FILE variables, resumes an existing
    session if present, and invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        repo_root: Repository root path. When provided, grants file
            permissions via allowed_tools and uses repo root as cwd.

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If the idea file does not exist
    """
    project.validate_idea()

    prompt = render_template("create-spec.md", {
        "IDEA_FILE": project.idea_file,
        "DISCUSSION_FILE": project.discussion_file,
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
            session_id=read_session_id(project.session_id_file),
        ),
    )
