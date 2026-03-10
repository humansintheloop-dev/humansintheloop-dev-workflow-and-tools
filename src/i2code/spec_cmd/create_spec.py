"""Create specification from an idea via Claude."""

from i2code.claude_cmd import build_allowed_tools_flag
from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.session_manager import build_session_args
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
            permissions via --allowedTools and uses repo root as cwd.

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

    session_args = build_session_args(project.session_id_file)
    cmd = ["claude"]

    if repo_root is not None:
        allowed_tools = build_allowed_tools_flag(repo_root, project.directory)
        cmd += ["--allowedTools", allowed_tools]

    cmd += session_args + [prompt]

    cwd = repo_root if repo_root is not None else project.directory
    return claude_runner.run_interactive(cmd, cwd=cwd)
