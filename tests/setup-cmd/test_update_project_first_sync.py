"""Tests for update_project first-sync flow.

When one file has no SHA marker, update_project renders the file-specific
first-sync prompt and (on success) writes the current SHA marker.
"""

import json
import os
import tempfile
from typing import NamedTuple
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project

from _update_project_helpers import (
    _DEFAULT_CURRENT_SHAS,
    assert_claude_md_marker_advanced,
    assert_settings_marker_advanced,
    per_file_subprocess_run,
)


class _FirstSyncCase(NamedTuple):
    kind: str
    template_name: str
    sha: str
    override: object = None
    expected_token: str = ""


_DEFAULT_CLAUDE_MD_TEMPLATE = "# Template CLAUDE.md content\n"
_DEFAULT_SETTINGS_TEMPLATE = {"permissions": {"allow": ["Bash(echo:*)"]}}


def _setup_first_sync_project(tmpdir, *, missing_kind, claude_md_template, settings_template):
    """Create project where exactly one file is missing its SHA marker.

    `missing_kind` is "claude_md" or "settings". The non-missing file is created
    with its SHA marker so it routes through the synced (empty-diff) branch.
    """
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    claude_md_content = "# Project\n"
    if missing_kind != "claude_md":
        claude_md_content += "<!-- claude-config-files-sha: AAA111 -->\n"
    with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
        f.write(claude_md_content)
    os.makedirs(os.path.join(project_dir, ".claude"))
    settings_allow = ["Bash(echo:*)"]
    if missing_kind != "settings":
        settings_allow.append("Bash(i2code-config-files-sha BBB222)")
    with open(os.path.join(project_dir, ".claude", "settings.local.json"), "w") as f:
        json.dump({"permissions": {"allow": settings_allow}}, f)
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
        f.write(claude_md_template)
    with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
        json.dump(settings_template, f)
    claude_md_relpath = os.path.relpath(os.path.join(config_dir, "CLAUDE.md"), tmpdir)
    settings_relpath = os.path.relpath(os.path.join(config_dir, "settings.local.json"), tmpdir)
    return project_dir, config_dir, claude_md_relpath, settings_relpath


def _run_first_sync(tmpdir, fakes, *, missing_kind, template_override=None):
    """Set up a first-sync scenario for `missing_kind` and call update_project.

    `template_override`, if set, replaces the source template content for the
    missing file (str for CLAUDE.md, dict for settings).
    """
    fake_runner, fake_renderer = fakes
    claude_md_template = _DEFAULT_CLAUDE_MD_TEMPLATE
    settings_template = _DEFAULT_SETTINGS_TEMPLATE
    if template_override is not None:
        if missing_kind == "claude_md":
            claude_md_template = template_override
        else:
            settings_template = template_override
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        _setup_first_sync_project(
            tmpdir, missing_kind=missing_kind,
            claude_md_template=claude_md_template,
            settings_template=settings_template,
        )
    )
    synced_relpath = settings_relpath if missing_kind == "claude_md" else claude_md_relpath
    per_file_shas = {
        claude_md_relpath: _DEFAULT_CURRENT_SHAS["claude_md"],
        settings_relpath: _DEFAULT_CURRENT_SHAS["settings"],
    }
    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = per_file_subprocess_run(
            tmpdir, per_file_shas=per_file_shas, per_file_diffs={synced_relpath: ""},
        )
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return project_dir


def _find_render_call(fake_renderer, template_name):
    matches = [c for c in fake_renderer.calls if c[0] == template_name]
    assert len(matches) == 1
    return matches[0]


_FIRST_SYNC_CASES = [
    pytest.param(
        _FirstSyncCase(
            kind="claude_md", template_name="update-project-claude-md.md", sha="CCC333",
            override="Hello template body", expected_token="Hello template body",
        ),
        id="claude_md",
    ),
    pytest.param(
        _FirstSyncCase(
            kind="settings", template_name="update-project-settings.md", sha="DDD444",
            override={"permissions": {"allow": ["Bash(unique-marker:*)"]}},
            expected_token="Bash(unique-marker:*)",
        ),
        id="settings",
    ),
]


def _assert_marker_advanced(kind, project_dir, sha):
    if kind == "claude_md":
        assert_claude_md_marker_advanced(project_dir, sha)
    else:
        assert_settings_marker_advanced(project_dir, sha)


@pytest.mark.unit
class TestFirstSync:

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_renders_first_sync_prompt(self, fake_runner, fake_renderer, case):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_first_sync(tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind)
            _, variables = _find_render_call(fake_renderer, case.template_name)
            assert variables["IS_FIRST_SYNC"] == "true"
            assert variables["PREVIOUS_SHA"] == ""

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_first_sync_prompt_contains_full_template_content(
        self, fake_runner, fake_renderer, case,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_first_sync(
                tmpdir, (fake_runner, fake_renderer),
                missing_kind=case.kind, template_override=case.override,
            )
            _, variables = _find_render_call(fake_renderer, case.template_name)
            assert case.expected_token in variables["CONFIG_DIFF"]
            assert "first sync" in variables["CONFIG_DIFF"].lower()

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_first_sync_invokes_claude(self, fake_runner, fake_renderer, case):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_first_sync(
                tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind,
            )
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_interactive"
            assert cmd[0] == "claude"
            assert cwd == project_dir

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_python_writes_sha_after_claude_success(
        self, fake_runner, fake_renderer, case,
    ):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_result(ClaudeResult(returncode=0))
            project_dir = _run_first_sync(
                tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind,
            )
            _assert_marker_advanced(case.kind, project_dir, case.sha)
