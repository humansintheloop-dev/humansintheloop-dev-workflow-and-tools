"""Update Claude configuration files from a project's customizations."""

import os
import sys


def update_claude_files(project_dir, config_dir, claude_runner, template_renderer):
    """Review project Claude files and update config-files templates.

    Validates both directories exist and that the project has at least
    one Claude file (CLAUDE.md or .claude/settings.local.json). Renders
    the ``update-claude-files-from-project.md`` template and invokes
    Claude interactively.

    Args:
        project_dir: Path to the project directory
        config_dir: Path to the config-files directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str

    Returns:
        ClaudeResult from Claude invocation

    Raises:
        SystemExit: If directories don't exist or project has no Claude files
    """
    if not os.path.isdir(project_dir):
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(config_dir):
        print(f"Error: Config directory not found: {config_dir}", file=sys.stderr)
        sys.exit(1)

    project_claude_md = os.path.join(project_dir, "CLAUDE.md")
    project_settings = os.path.join(project_dir, ".claude", "settings.local.json")

    if not os.path.isfile(project_claude_md) and not os.path.isfile(project_settings):
        print(
            "Error: No Claude files found in project. Expected at least one of:",
            file=sys.stderr,
        )
        print(f"  - {project_claude_md}", file=sys.stderr)
        print(f"  - {project_settings}", file=sys.stderr)
        sys.exit(1)

    config_claude_md = os.path.join(config_dir, "CLAUDE.md")
    config_settings = os.path.join(config_dir, "settings.local.json")

    prompt = template_renderer("update-claude-files-from-project.md", {
        "PROJECT_DIR": project_dir,
        "PROJECT_CLAUDE_MD": project_claude_md,
        "PROJECT_SETTINGS": project_settings,
        "CONFIG_CLAUDE_MD": config_claude_md,
        "CONFIG_SETTINGS": config_settings,
    })

    cmd = ["claude", prompt]

    return claude_runner.run_interactive(cmd, cwd=project_dir)
