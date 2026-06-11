"""Tests for update_project behavior when project files are missing or already in sync.

When a project file is missing or its diff is empty, update_project should copy
the template (if missing) and advance the SHA marker without invoking Claude.
"""

import os
import tempfile

import pytest

from _update_project_helpers import (
    assert_claude_md_marker_advanced,
    assert_settings_marker_advanced,
    read_settings_allow,
    run_update_with_per_file_mock,
)


@pytest.mark.unit
class TestMissingFileCopy:

    def _run_missing_claude_md(self, tmpdir, fake_runner, fake_renderer):
        return run_update_with_per_file_mock(
            tmpdir, (fake_runner, fake_renderer),
            markers={"settings": "BBB222"},
        )

    def _run_missing_settings(self, tmpdir, fake_runner, fake_renderer):
        return run_update_with_per_file_mock(
            tmpdir, (fake_runner, fake_renderer),
            markers={"claude_md": "CCC333"},
        )

    def test_copies_missing_claude_md_from_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            with open(os.path.join(project_dir, "CLAUDE.md")) as f:
                assert f.read().startswith("# Template CLAUDE.md content\n")

    def test_writes_claude_md_sha_marker_after_copy(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            assert_claude_md_marker_advanced(project_dir, "CCC333")

    def test_no_claude_invocation_when_claude_md_missing(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            assert len(fake_runner.calls) == 0

    def test_copies_missing_settings_from_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            assert "Bash(echo:*)" in read_settings_allow(project_dir)

    def test_writes_settings_sha_marker_after_copy(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            assert_settings_marker_advanced(project_dir, "DDD444")

    def test_creates_claude_directory_if_absent(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            assert os.path.isdir(os.path.join(project_dir, ".claude"))

    def test_scenario_s6_both_files_missing_no_claude_invocations(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
            )
            assert_claude_md_marker_advanced(project_dir, "CCC333")
            assert_settings_marker_advanced(project_dir, "DDD444")
            assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestEmptyDiffSkip:

    def _run_and_assert_claude_md_synced(
        self, tmpdir, fake_runner, fake_renderer, markers,
    ):
        project_dir = run_update_with_per_file_mock(
            tmpdir, (fake_runner, fake_renderer), markers=markers,
        )
        assert len(fake_runner.calls) == 0
        assert_claude_md_marker_advanced(project_dir, "CCC333")
        return project_dir

    def test_skips_claude_for_both_files_and_advances_both_markers(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_and_assert_claude_md_synced(
                tmpdir, fake_runner, fake_renderer,
                {"claude_md": "AAA111", "settings": "BBB222"},
            )
            assert_settings_marker_advanced(project_dir, "DDD444")

    def test_scenario_s4_missing_claude_md_settings_synced(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_and_assert_claude_md_synced(
                tmpdir, fake_runner, fake_renderer,
                {"settings": "BBB222"},
            )
            assert "Bash(i2code-config-files-sha DDD444)" in read_settings_allow(project_dir)
