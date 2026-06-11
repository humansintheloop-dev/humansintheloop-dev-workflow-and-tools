"""Shared helpers for update_project tests.

Splitting these out keeps each test module focused on one responsibility.
"""

import json
import os
import subprocess
from unittest.mock import patch

from i2code.setup_cmd.update_project import update_project

_DEFAULT_CURRENT_SHAS = {"claude_md": "CCC333", "settings": "DDD444"}


def create_project_dir(tmpdir, *, claude_md_content=None):
    """Create a project directory, optionally with CLAUDE.md."""
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    if claude_md_content is not None:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write(claude_md_content)
    return project_dir


def create_config_dir(tmpdir):
    """Create a config directory."""
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    return config_dir


def per_file_subprocess_run(repo_root, *, per_file_shas=None, per_file_diffs=None):
    """Mock subprocess.run with per-file SHA/diff control keyed by relpath.

    per_file_shas maps `relpath -> SHA string` for `git log -1 --format=%H -- <relpath>`.
    per_file_diffs maps `relpath -> diff string` for `git diff <prev>..<curr> -- <relpath>`.
    Matching is done by the final argv element (the relpath after `--`).
    """
    per_file_shas = per_file_shas or {}
    per_file_diffs = per_file_diffs or {}

    def mock_run(cmd, capture_output=False, text=False, check=False, cwd=None):
        cmd_str = " ".join(cmd)
        result = subprocess.CompletedProcess(cmd, 0)
        result.stderr = ""
        if "rev-parse --show-toplevel" in cmd_str:
            result.stdout = repo_root + "\n"
        elif "log -1 --format=%H" in cmd_str:
            relpath = cmd[-1]
            result.stdout = per_file_shas.get(relpath, "") + "\n"
        elif "diff" in cmd_str:
            relpath = cmd[-1]
            result.stdout = per_file_diffs.get(relpath, "") + "\n"
        else:
            result.stdout = ""
        return result
    return mock_run


def read_settings_allow(project_dir):
    with open(os.path.join(project_dir, ".claude", "settings.local.json")) as f:
        return json.load(f)["permissions"]["allow"]


def assert_claude_md_marker_advanced(project_dir, sha):
    with open(os.path.join(project_dir, "CLAUDE.md")) as f:
        content = f.read().rstrip("\n")
    assert content.endswith(f"<!-- claude-config-files-sha: {sha} -->")


def assert_settings_marker_advanced(project_dir, sha):
    sha_entries = [e for e in read_settings_allow(project_dir)
                   if "i2code-config-files-sha" in e]
    assert sha_entries == [f"Bash(i2code-config-files-sha {sha})"]


def setup_per_file_project(tmpdir, markers):
    """Create project_dir + config_dir with templates, returning paths and relpaths.

    `markers` is a dict; if it contains `"claude_md"` the project's CLAUDE.md is
    created with that SHA marker, otherwise the file is omitted. Same convention
    for `"settings"` and `.claude/settings.local.json`. The config_dir is always
    populated with both template files. Relpaths are relative to tmpdir (the repo
    root).

    Returns (project_dir, config_dir, claude_md_relpath, settings_relpath).
    """
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    if "claude_md" in markers:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write(f"# Project\n<!-- claude-config-files-sha: {markers['claude_md']} -->\n")
    if "settings" in markers:
        os.makedirs(os.path.join(project_dir, ".claude"))
        with open(os.path.join(project_dir, ".claude", "settings.local.json"), "w") as f:
            json.dump(
                {"permissions": {"allow": [
                    "Bash(echo:*)",
                    f"Bash(i2code-config-files-sha {markers['settings']})",
                ]}},
                f,
            )

    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
        f.write("# Template CLAUDE.md content\n")
    with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
        json.dump({"permissions": {"allow": ["Bash(echo:*)"]}}, f)

    claude_md_relpath = os.path.relpath(os.path.join(config_dir, "CLAUDE.md"), tmpdir)
    settings_relpath = os.path.relpath(
        os.path.join(config_dir, "settings.local.json"), tmpdir,
    )
    return project_dir, config_dir, claude_md_relpath, settings_relpath


def run_update_with_per_file_mock(tmpdir, fakes, *, markers=None, diffs_by_kind=None):
    """Set up project + mock subprocess + invoke update_project. Returns project_dir.

    `markers` is a dict mapping file-kind ("claude_md", "settings") to its previous
    SHA marker; absent keys mean that project file is not created. `diffs_by_kind`
    maps file-kind to its per-file diff text; absent kinds default to an empty diff.
    """
    fake_runner, fake_renderer = fakes
    markers = markers or {}
    diffs_by_kind = diffs_by_kind or {}
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        setup_per_file_project(tmpdir, markers)
    )
    relpath_by_kind = {"claude_md": claude_md_relpath, "settings": settings_relpath}
    per_file_diffs = {relpath_by_kind[k]: d for k, d in diffs_by_kind.items()}
    per_file_shas = {
        relpath_by_kind[k]: sha for k, sha in _DEFAULT_CURRENT_SHAS.items()
    }
    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = per_file_subprocess_run(
            tmpdir, per_file_shas=per_file_shas, per_file_diffs=per_file_diffs,
        )
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return project_dir
