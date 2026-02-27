"""Push template updates into a project's Claude files."""

import os
import re
import subprocess
import sys


def update_project(project_dir, config_dir, claude_runner, template_renderer):
    """Push template updates from config-dir into a project's Claude files.

    Validates directories, derives git repo root from config-dir, extracts
    previous SHA from project's CLAUDE.md, generates git diff between
    previous and current config-files SHA, renders the template, and
    invokes Claude interactively.

    Args:
        project_dir: Path to the project directory
        config_dir: Path to the config-files directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str

    Returns:
        ClaudeResult from Claude invocation

    Raises:
        SystemExit: If directories don't exist
    """
    if not os.path.isdir(project_dir):
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        raise SystemExit(1)

    if not os.path.isdir(config_dir):
        print(f"Error: Config directory not found: {config_dir}", file=sys.stderr)
        raise SystemExit(1)

    project_claude_md = os.path.join(project_dir, "CLAUDE.md")
    project_settings = os.path.join(project_dir, ".claude", "settings.local.json")
    config_claude_md = os.path.join(config_dir, "CLAUDE.md")
    config_settings = os.path.join(config_dir, "settings.local.json")

    previous_sha = _extract_previous_sha(project_claude_md)

    repo_root = _get_repo_root(config_dir)
    current_sha = _get_current_sha(repo_root, config_dir)
    config_diff = _get_config_diff(repo_root, config_dir, previous_sha, current_sha)

    prompt = template_renderer("update-project-claude-files.md", {
        "PROJECT_DIR": project_dir,
        "PROJECT_CLAUDE_MD": project_claude_md,
        "PROJECT_SETTINGS": project_settings,
        "CONFIG_CLAUDE_MD": config_claude_md,
        "CONFIG_SETTINGS": config_settings,
        "CURRENT_SHA": current_sha,
        "PREVIOUS_SHA": previous_sha,
        "CONFIG_DIFF": config_diff,
    })

    cmd = ["claude", prompt]
    return claude_runner.run_interactive(cmd, cwd=project_dir)


def _extract_previous_sha(project_claude_md):
    """Extract previous config-files SHA from project's CLAUDE.md."""
    if not os.path.isfile(project_claude_md):
        return ""
    try:
        with open(project_claude_md) as f:
            content = f.read()
        match = re.search(r"claude-config-files-sha:\s*([a-f0-9]+)", content)
        return match.group(1) if match else ""
    except OSError:
        return ""


def _get_repo_root(config_dir):
    """Derive git repo root from config-dir path."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=config_dir,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _get_current_sha(repo_root, config_dir):
    """Get the current SHA of the config-files directory."""
    if not repo_root:
        return ""
    config_rel_path = os.path.relpath(config_dir, repo_root)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", config_rel_path + "/"],
        capture_output=True, text=True, cwd=repo_root,
    )
    return result.stdout.strip()


def _get_config_diff(repo_root, config_dir, previous_sha, current_sha):
    """Generate diff of config-files between previous and current SHA."""
    if not all([previous_sha, current_sha, repo_root]):
        return "No previous SHA found. This appears to be the first sync. Full template contents will be used as reference."
    config_rel_path = os.path.relpath(config_dir, repo_root)
    result = subprocess.run(
        ["git", "diff", f"{previous_sha}..{current_sha}", "--", config_rel_path + "/"],
        capture_output=True, text=True, cwd=repo_root,
    )
    if result.returncode != 0:
        return "Unable to generate diff - previous SHA not found in history"
    return result.stdout.strip()
