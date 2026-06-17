"""Push template updates into a project's Claude files."""

import json
import os
import re
import shutil
import subprocess
import sys
from typing import NamedTuple

from i2code.implement.claude_runner import ClaudeCodeCommand, ClaudeResult


class _FileSpec(NamedTuple):
    project_path: str
    source_path: str
    template_relpath: str
    read_sha: object
    write_sha: object
    template_name: str
    project_var: str
    source_var: str


class _Context(NamedTuple):
    project_dir: str
    repo_root: str
    claude_runner: object
    template_renderer: object


class _RenderSpec(NamedTuple):
    previous_sha: str
    config_diff: str
    is_first_sync: str


CLAUDE_MD_NAME = "CLAUDE.md"
SETTINGS_RELPATH = os.path.join(".claude", "settings.local.json")
SETTINGS_TEMPLATE_NAME = "settings.local.json"
CLAUDE_MD_SHA_MARKER = "claude-config-files-sha"
SETTINGS_SHA_MARKER = "i2code-config-files-sha"
CLAUDE_MD_TEMPLATE = "update-project-claude-md.md"
SETTINGS_TEMPLATE = "update-project-settings.md"
FIRST_SYNC_PREAMBLE = "First sync — full current template content follows:\n\n"


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
    _validate_directories(project_dir, config_dir)

    ctx = _Context(
        project_dir=project_dir,
        repo_root=_get_repo_root(config_dir),
        claude_runner=claude_runner,
        template_renderer=template_renderer,
    )
    for spec in _build_file_specs(project_dir, config_dir, ctx.repo_root):
        result = _process_file(spec, ctx)
        if result is not None and result.returncode != 0:
            return result

    return ClaudeResult(returncode=0)


def _validate_directories(project_dir, config_dir):
    if not os.path.isdir(project_dir):
        print(f"Error: Project directory not found: {project_dir}", file=sys.stderr)
        raise SystemExit(1)
    if not os.path.isdir(config_dir):
        print(f"Error: Config directory not found: {config_dir}", file=sys.stderr)
        raise SystemExit(1)


def _build_file_specs(project_dir, config_dir, repo_root):
    claude_md_source = os.path.join(config_dir, CLAUDE_MD_NAME)
    settings_source = os.path.join(config_dir, SETTINGS_TEMPLATE_NAME)
    return [
        _FileSpec(
            project_path=os.path.join(project_dir, CLAUDE_MD_NAME),
            source_path=claude_md_source,
            template_relpath=_config_file_relpath(claude_md_source, repo_root),
            read_sha=_read_claude_md_sha,
            write_sha=_write_claude_md_sha,
            template_name=CLAUDE_MD_TEMPLATE,
            project_var="PROJECT_CLAUDE_MD",
            source_var="CONFIG_CLAUDE_MD",
        ),
        _FileSpec(
            project_path=os.path.join(project_dir, SETTINGS_RELPATH),
            source_path=settings_source,
            template_relpath=_config_file_relpath(settings_source, repo_root),
            read_sha=_read_settings_sha,
            write_sha=_write_settings_sha,
            template_name=SETTINGS_TEMPLATE,
            project_var="PROJECT_SETTINGS",
            source_var="CONFIG_SETTINGS",
        ),
    ]


def _process_file(spec, ctx):
    if not os.path.isfile(spec.project_path):
        _copy_template_file(spec.source_path, spec.project_path)
        spec.write_sha(spec.project_path, _get_per_file_current_sha(ctx.repo_root, spec.template_relpath))
        return None
    previous_sha = spec.read_sha(spec.project_path)
    current_sha = _get_per_file_current_sha(ctx.repo_root, spec.template_relpath)
    if not previous_sha:
        return _run_first_sync(spec, current_sha, ctx)
    diff = _get_per_file_diff(ctx.repo_root, spec.template_relpath, previous_sha, current_sha)
    if diff == "":
        spec.write_sha(spec.project_path, current_sha)
        return None
    render = _RenderSpec(
        previous_sha=previous_sha, config_diff=diff, is_first_sync="false",
    )
    return _render_and_advance_sha(spec, ctx, current_sha, render)


def _build_variables(spec, ctx, current_sha, render):
    return {
        "PROJECT_DIR": ctx.project_dir,
        spec.project_var: spec.project_path,
        spec.source_var: spec.source_path,
        "CURRENT_SHA": current_sha,
        "PREVIOUS_SHA": render.previous_sha,
        "CONFIG_DIFF": render.config_diff,
        "IS_FIRST_SYNC": render.is_first_sync,
    }


def _render_and_advance_sha(spec, ctx, current_sha, render):
    variables = _build_variables(spec, ctx, current_sha, render)
    prompt = ctx.template_renderer(spec.template_name, variables)
    result = ctx.claude_runner.execute(
        ClaudeCodeCommand(prompt=prompt, cwd=ctx.project_dir, interactive=True),
    )
    if result.returncode == 0:
        spec.write_sha(spec.project_path, current_sha)
    return result


def _run_first_sync(spec, current_sha, ctx):
    with open(spec.source_path) as f:
        template_content = f.read()
    render = _RenderSpec(
        previous_sha="",
        config_diff=FIRST_SYNC_PREAMBLE + template_content,
        is_first_sync="true",
    )
    return _render_and_advance_sha(spec, ctx, current_sha, render)


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
