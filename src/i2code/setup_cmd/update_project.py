"""Push template updates into a project's Claude files."""

import json
import os
import re
import shutil
import subprocess
import sys
from typing import NamedTuple

from i2code.implement.claude_runner import ClaudeResult


class _FileSpec(NamedTuple):
    project_path: str
    source_path: str
    read_sha: object
    write_sha: object

CLAUDE_MD_NAME = "CLAUDE.md"
SETTINGS_RELPATH = os.path.join(".claude", "settings.local.json")
SETTINGS_TEMPLATE_NAME = "settings.local.json"
CLAUDE_MD_SHA_MARKER = "claude-config-files-sha"
SETTINGS_SHA_MARKER = "i2code-config-files-sha"


def update_project(project_dir, config_dir, claude_runner, template_renderer):
    """Push template updates from config-dir into a project's Claude files.

    Processes CLAUDE.md, then .claude/settings.local.json with per-file routing.
    Missing project files are copied from config_dir and their per-file SHA marker
    written; no Claude invocation occurs for that file. Settings files whose
    previous-SHA marker is present and per-file diff is empty are skipped.

    Args:
        project_dir: Path to the project directory
        config_dir: Path to the config-files directory
        claude_runner: ClaudeRunner instance for invoking Claude
        template_renderer: Callable(template_name, variables) -> str

    Returns:
        ClaudeResult from the processing flow

    Raises:
        SystemExit: If directories don't exist
    """
    del claude_runner, template_renderer
    _validate_directories(project_dir, config_dir)

    repo_root = _get_repo_root(config_dir)
    for spec in _build_file_specs(project_dir, config_dir):
        _process_file(spec, repo_root)

    return ClaudeResult(returncode=0)


def _validate_directories(project_dir, config_dir):
    if not os.path.isdir(project_dir):
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        raise SystemExit(1)
    if not os.path.isdir(config_dir):
        print(f"Error: Config directory not found: {config_dir}", file=sys.stderr)
        raise SystemExit(1)


def _build_file_specs(project_dir, config_dir):
    return [
        _FileSpec(
            project_path=os.path.join(project_dir, CLAUDE_MD_NAME),
            source_path=os.path.join(config_dir, CLAUDE_MD_NAME),
            read_sha=_read_claude_md_sha,
            write_sha=_write_claude_md_sha,
        ),
        _FileSpec(
            project_path=os.path.join(project_dir, SETTINGS_RELPATH),
            source_path=os.path.join(config_dir, SETTINGS_TEMPLATE_NAME),
            read_sha=_read_settings_sha,
            write_sha=_write_settings_sha,
        ),
    ]


def _process_file(spec, repo_root):
    relpath = _config_file_relpath(spec.source_path, repo_root)
    if not os.path.isfile(spec.project_path):
        _copy_template_file(spec.source_path, spec.project_path)
        spec.write_sha(spec.project_path, _get_per_file_current_sha(repo_root, relpath))
        return
    previous_sha = spec.read_sha(spec.project_path)
    if not previous_sha:
        return
    current_sha = _get_per_file_current_sha(repo_root, relpath)
    _get_per_file_diff(repo_root, relpath, previous_sha, current_sha)


def _config_file_relpath(config_file_path, repo_root):
    if not repo_root:
        return config_file_path
    return os.path.relpath(config_file_path, repo_root)


def _copy_template_file(source_path, dest_path):
    parent = os.path.dirname(dest_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    shutil.copy(source_path, dest_path)


def _get_per_file_current_sha(repo_root, template_file_relpath):
    if not repo_root:
        return ""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", template_file_relpath],
        capture_output=True, text=True, cwd=repo_root,
    )
    return result.stdout.strip()


def _get_per_file_diff(repo_root, template_file_relpath, prev_sha, curr_sha):
    if not all([repo_root, prev_sha, curr_sha]):
        return ""
    result = subprocess.run(
        ["git", "diff", f"{prev_sha}..{curr_sha}", "--", template_file_relpath],
        capture_output=True, text=True, cwd=repo_root,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _write_claude_md_sha(claude_md_path, sha):
    """Write/replace the SHA marker as the last line of CLAUDE.md."""
    marker_line = f"<!-- {CLAUDE_MD_SHA_MARKER}: {sha} -->"
    with open(claude_md_path) as f:
        content = f.read()
    content = re.sub(rf"\n*<!-- {CLAUDE_MD_SHA_MARKER}:[^>]*-->\n*", "", content)
    if content and not content.endswith("\n"):
        content += "\n"
    content += marker_line + "\n"
    with open(claude_md_path, "w") as f:
        f.write(content)


def _write_settings_sha(settings_path, sha):
    """Write/replace the SHA marker entry in permissions.allow as the last entry."""
    with open(settings_path) as f:
        data = json.load(f)
    permissions = data.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    marker_pattern = re.compile(rf"^Bash\({SETTINGS_SHA_MARKER}\s+")
    allow[:] = [entry for entry in allow if not marker_pattern.match(entry)]
    allow.append(f"Bash({SETTINGS_SHA_MARKER} {sha})")
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)


def _read_claude_md_sha(claude_md_path):
    if not os.path.isfile(claude_md_path):
        return ""
    with open(claude_md_path) as f:
        content = f.read()
    match = re.search(rf"<!-- {CLAUDE_MD_SHA_MARKER}:\s*([a-zA-Z0-9]+)\s*-->", content)
    return match.group(1) if match else ""


def _read_settings_sha(settings_path):
    if not os.path.isfile(settings_path):
        return ""
    with open(settings_path) as f:
        content = f.read()
    match = re.search(rf"Bash\({SETTINGS_SHA_MARKER}\s+([a-zA-Z0-9]+)\)", content)
    return match.group(1) if match else ""


def _get_repo_root(config_dir):
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, cwd=config_dir,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
