"""Tests for update_project per-file SHA reading from CLAUDE.md / settings markers.

Verifies that update_project reads each file's previous SHA from its own marker
and passes it to `git diff` for that file.
"""

import tempfile
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project

from _update_project_helpers import (
    _DEFAULT_CURRENT_SHAS,
    per_file_subprocess_run,
    setup_per_file_project,
)


def _run_capturing_git_calls(tmpdir, fakes, markers):
    """Run update_project with per-file mock subprocess and capture all git calls.

    Returns (captured_cmds, claude_md_relpath, settings_relpath).
    """
    fake_runner, fake_renderer = fakes
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        setup_per_file_project(tmpdir, markers)
    )
    per_file_diffs = {claude_md_relpath: "", settings_relpath: ""}
    per_file_shas = {
        claude_md_relpath: _DEFAULT_CURRENT_SHAS["claude_md"],
        settings_relpath: _DEFAULT_CURRENT_SHAS["settings"],
    }
    base_mock = per_file_subprocess_run(
        tmpdir, per_file_shas=per_file_shas, per_file_diffs=per_file_diffs,
    )
    captured = []

    def tracking(cmd, capture_output=False, text=False, check=False, cwd=None):
        captured.append(cmd)
        return base_mock(
            cmd, capture_output=capture_output, text=text, check=check, cwd=cwd,
        )

    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = tracking
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return captured, claude_md_relpath, settings_relpath


@pytest.mark.unit
class TestPerFileShaReading:

    @pytest.mark.parametrize(
        "case",
        [
            pytest.param((1, "AAA111..CCC333"), id="claude_md"),
            pytest.param((2, "BBB222..DDD444"), id="settings"),
        ],
    )
    def test_reads_previous_sha_from_marker(self, fake_runner, fake_renderer, case):
        relpath_idx, expected_range = case
        with tempfile.TemporaryDirectory() as tmpdir:
            captured_and_relpaths = _run_capturing_git_calls(
                tmpdir, (fake_runner, fake_renderer),
                markers={"claude_md": "AAA111", "settings": "BBB222"},
            )
            captured = captured_and_relpaths[0]
            relpath = captured_and_relpaths[relpath_idx]
            diff_calls = [
                c for c in captured
                if "diff" in " ".join(c) and c[-1] == relpath
            ]
            assert len(diff_calls) == 1
            assert expected_range in " ".join(diff_calls[0])

    def test_per_file_diff_calls_use_per_file_previous_shas(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            captured, claude_md_relpath, settings_relpath = _run_capturing_git_calls(
                tmpdir, (fake_runner, fake_renderer),
                markers={"claude_md": "AAA111", "settings": "BBB222"},
            )
            diff_calls = [c for c in captured if "diff" in " ".join(c)]
            assert len(diff_calls) == 2
            claude_md_diff = next(
                c for c in diff_calls if c[-1] == claude_md_relpath
            )
            settings_diff = next(
                c for c in diff_calls if c[-1] == settings_relpath
            )
            assert "AAA111..CCC333" in " ".join(claude_md_diff)
            assert "BBB222..DDD444" in " ".join(settings_diff)
