"""Tests for the routine update flow and abort-on-failure behavior.

Routine update: both files have SHA markers and non-empty per-file diffs, so
update_project renders both prompts and invokes Claude twice. If the first
Claude invocation fails, the second render/invocation does not happen and
neither SHA marker is advanced.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project

from _update_project_helpers import (
    _DEFAULT_CURRENT_SHAS,
    assert_claude_md_marker_advanced,
    assert_settings_marker_advanced,
    per_file_subprocess_run,
    read_settings_allow,
    run_update_with_per_file_mock,
    setup_per_file_project,
)

_S1_MARKERS = {"claude_md": "AAA111", "settings": "BBB222"}
_S1_DIFFS = {"claude_md": "diff-for-claude-md", "settings": "diff-for-settings"}


def _run_routine_update(tmpdir, fakes, *, diffs_by_kind=None):
    """Run scenario S-1: both markers present, custom per-file diffs."""
    return run_update_with_per_file_mock(
        tmpdir, fakes,
        markers=_S1_MARKERS,
        diffs_by_kind=diffs_by_kind if diffs_by_kind is not None else _S1_DIFFS,
    )


def _run_update_capturing_result(tmpdir, fakes, *, markers=None, diffs_by_kind=None):
    """Like run_update_with_per_file_mock but returns (result, project_dir)."""
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
        result = update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return result, project_dir


@pytest.mark.unit
class TestRoutineUpdate:

    def test_two_renders_in_claude_md_then_settings_order(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            assert [call[0] for call in fake_renderer.calls] == [
                "update-project-claude-md.md",
                "update-project-settings.md",
            ]

    def test_each_render_has_per_file_diff_and_shas(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            claude_vars = fake_renderer.calls[0][1]
            assert claude_vars["IS_FIRST_SYNC"] == "false"
            assert claude_vars["PREVIOUS_SHA"] == "AAA111"
            assert claude_vars["CURRENT_SHA"] == "CCC333"
            assert claude_vars["CONFIG_DIFF"] == "diff-for-claude-md"
            settings_vars = fake_renderer.calls[1][1]
            assert settings_vars["IS_FIRST_SYNC"] == "false"
            assert settings_vars["PREVIOUS_SHA"] == "BBB222"
            assert settings_vars["CURRENT_SHA"] == "DDD444"
            assert settings_vars["CONFIG_DIFF"] == "diff-for-settings"

    def test_two_claude_invocations_in_order(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            assert len(fake_runner.calls) == 2
            for method, cmd, cwd in fake_runner.calls:
                assert method == "execute"
                assert cmd.interactive is True
                assert cwd == project_dir
            assert "template=update-project-claude-md.md" in fake_runner.calls[0][1].prompt
            assert "template=update-project-settings.md" in fake_runner.calls[1][1].prompt

    def test_scenario_s1_both_markers_advanced(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_results([
                ClaudeResult(returncode=0), ClaudeResult(returncode=0),
            ])
            project_dir = _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            assert_claude_md_marker_advanced(project_dir, "CCC333")
            assert_settings_marker_advanced(project_dir, "DDD444")

    def test_scenario_s2_only_claude_md_changed(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_result(ClaudeResult(returncode=0))
            project_dir = run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
                markers=_S1_MARKERS,
                diffs_by_kind={"claude_md": "diff-for-claude-md"},
            )
            assert len(fake_runner.calls) == 1
            assert "template=update-project-claude-md.md" in fake_runner.calls[0][1].prompt
            assert_claude_md_marker_advanced(project_dir, "CCC333")
            assert_settings_marker_advanced(project_dir, "DDD444")


@pytest.mark.unit
class TestAbortOnFailure:

    def _run_s1_with_failing_first_claude(self, tmpdir, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult
        fake_runner.set_result(ClaudeResult(returncode=2))
        return _run_update_capturing_result(
            tmpdir, (fake_runner, fake_renderer),
            markers=_S1_MARKERS, diffs_by_kind=_S1_DIFFS,
        )

    def test_no_second_render_when_first_claude_fails(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_s1_with_failing_first_claude(tmpdir, fake_runner, fake_renderer)
            assert len(fake_renderer.calls) == 1
            assert fake_renderer.calls[0][0] == "update-project-claude-md.md"
            assert len(fake_runner.calls) == 1

    def test_no_sha_writes_when_first_claude_fails(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, project_dir = self._run_s1_with_failing_first_claude(
                tmpdir, fake_runner, fake_renderer,
            )
            with open(os.path.join(project_dir, "CLAUDE.md")) as f:
                assert "<!-- claude-config-files-sha: AAA111 -->" in f.read()
            allow = read_settings_allow(project_dir)
            assert "Bash(i2code-config-files-sha BBB222)" in allow
            assert "Bash(i2code-config-files-sha DDD444)" not in allow

    def test_returns_failing_claude_result(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            result, _ = self._run_s1_with_failing_first_claude(
                tmpdir, fake_runner, fake_renderer,
            )
            assert result.returncode == 2

    def test_returns_zero_when_no_claude_invocations(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            result, _ = _run_update_capturing_result(
                tmpdir, (fake_runner, fake_renderer),
            )
            assert len(fake_runner.calls) == 0
            assert result.returncode == 0
