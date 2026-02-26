"""Brainstorm idea: creates idea file, launches editor, invokes Claude."""

import glob
import os
import shutil
import subprocess

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.session_manager import get_or_create_session_args
from i2code.template_renderer import render_template

IDEA_TEMPLATE_TEXT = "PLEASE DESCRIBE YOUR IDEA"


def detect_editor() -> list[str]:
    """Detect the best available editor.

    Detection order: code --wait, $VISUAL, $EDITOR, vi.

    Returns:
        Editor command as a list of strings
    """
    if shutil.which("code"):
        return ["code", "--wait"]
    visual = os.environ.get("VISUAL")
    if visual:
        return [visual]
    editor = os.environ.get("EDITOR")
    if editor:
        return [editor]
    return ["vi"]


def brainstorm_idea(
    project: IdeaProject,
    claude_runner,
    *,
    run_editor=None,
) -> ClaudeResult:
    """Brainstorm an idea: create file, launch editor, invoke Claude.

    Creates the idea directory if missing. If no idea file exists,
    creates one with template text and opens it in the detected editor.
    Then renders the brainstorm-idea.md template and invokes Claude
    with session management.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        run_editor: Callback to launch editor, receives command list.
                    If None, uses subprocess.run.

    Returns:
        ClaudeResult from the Claude invocation
    """
    idea_file_exists = bool(
        glob.glob(os.path.join(project.directory, f"{project.name}-idea.*"))
    )

    if not idea_file_exists:
        os.makedirs(project.directory, exist_ok=True)
        idea_file = os.path.join(project.directory, f"{project.name}-idea.md")
        with open(idea_file, "w") as f:
            f.write(IDEA_TEMPLATE_TEXT + "\n")

        editor_cmd = detect_editor()
        full_cmd = editor_cmd + [idea_file]

        if run_editor is not None:
            run_editor(full_cmd)
        else:
            subprocess.run(full_cmd, check=False)

    prompt = render_template("brainstorm-idea.md", {
        "IDEA_FILE": project.idea_file,
        "DISCUSSION_FILE": project.discussion_file,
    })

    session_args = get_or_create_session_args(project.session_id_file)
    cmd = ["claude"] + session_args + [prompt]

    return claude_runner.run_interactive(cmd, cwd=project.directory)
