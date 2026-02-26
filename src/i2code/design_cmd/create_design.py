"""Create design document from a specification via Claude."""

import os
import sys
from datetime import datetime

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.session_manager import build_session_args
from i2code.template_renderer import render_template


def _archive_existing_design(project: IdeaProject) -> None:
    """Move existing design file to archive/ subdirectory with timestamp."""
    if not os.path.isfile(project.design_file):
        return

    archive_dir = os.path.join(project.directory, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_name = f"{project.name}-design-{timestamp}.md"
    archive_path = os.path.join(archive_dir, archive_name)
    os.rename(project.design_file, archive_path)
    print(f"Archived existing design to {archive_path}", file=sys.stderr)


def create_design(
    project: IdeaProject,
    claude_runner,
    *,
    plugin_skills_fn=None,
) -> ClaudeResult:
    """Generate a design document from idea and spec files using Claude.

    Validates idea and spec files exist, archives any existing design file,
    renders the create-design-doc.md template, and invokes Claude interactively.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        plugin_skills_fn: Callable returning comma-separated plugin skills string

    Returns:
        ClaudeResult from the Claude invocation

    Raises:
        SystemExit: If idea or spec file does not exist
    """
    project.validate_idea()
    project.validate_spec()

    _archive_existing_design(project)

    design_skills = plugin_skills_fn() if plugin_skills_fn else ""

    prompt = render_template("create-design-doc.md", {
        "IDEA_FILE": project.idea_file,
        "DISCUSSION_FILE": project.discussion_file,
        "SPEC_FILE": project.spec_file,
        "DESIGN_SKILLS": design_skills,
    })

    session_args = build_session_args(project.session_id_file)
    cmd = ["claude"] + session_args + [prompt]

    return claude_runner.run_interactive(cmd, cwd=project.directory)
