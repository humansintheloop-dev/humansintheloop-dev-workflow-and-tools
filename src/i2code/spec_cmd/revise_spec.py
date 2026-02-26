"""Revise specification via Claude."""

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject


def revise_spec(project: IdeaProject, claude_runner) -> ClaudeResult:
    """Revise an existing specification interactively via Claude.

    Validates that both idea and spec files exist, constructs an inline
    prompt referencing the idea, discussion, and spec file paths, and
    invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If the idea or spec file does not exist
    """
    project.validate_idea()
    project.validate_spec()

    prompt = (
        "Here are three files:\n"
        "\n"
        f"* {project.idea_file} - the file containing the idea description\n"
        f"* {project.discussion_file} - the file where questions and answers "
        "were saved when brainstorming the idea\n"
        f"* {project.spec_file}  - a comprehensive, developer-ready "
        "specification that was generated as a result of brainstorming\n"
        "\n"
        "I will ask you to make changes to the specification\n"
    )

    cmd = ["claude", prompt]

    return claude_runner.run_interactive(cmd, cwd=project.directory)
