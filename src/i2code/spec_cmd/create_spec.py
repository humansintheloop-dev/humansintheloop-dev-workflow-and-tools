"""Create specification from an idea via Claude."""

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.session_manager import build_session_args
from i2code.template_renderer import render_template


def create_spec(project: IdeaProject, claude_runner) -> ClaudeResult:
    """Generate a specification from an idea file using Claude.

    Validates the idea file exists, renders the create-spec.md template
    with IDEA_FILE and DISCUSSION_FILE variables, resumes an existing
    session if present, and invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude

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
    cmd = ["claude"] + session_args + [prompt]

    return claude_runner.run_interactive(cmd, cwd=project.directory)
