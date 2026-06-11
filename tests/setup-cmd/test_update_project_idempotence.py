"""Tests for update_project idempotence and prompt-template cleanup."""

import os
import tempfile
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project

from _update_project_helpers import (
    _DEFAULT_CURRENT_SHAS,
    per_file_subprocess_run,
    setup_per_file_project,
)

_S1_MARKERS = {"claude_md": "AAA111", "settings": "BBB222"}

_PROMPT_TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "src", "i2code", "prompt-templates",
)


@pytest.mark.unit
class TestIdempotenceAndCleanup:

    def test_second_consecutive_run_invokes_claude_zero_times(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, config_dir, claude_md_relpath, settings_relpath = (
                setup_per_file_project(tmpdir, _S1_MARKERS)
            )
            per_file_shas = {
                claude_md_relpath: _DEFAULT_CURRENT_SHAS["claude_md"],
                settings_relpath: _DEFAULT_CURRENT_SHAS["settings"],
            }
            first_run_diffs = {
                claude_md_relpath: "diff-for-claude-md",
                settings_relpath: "diff-for-settings",
            }
            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = per_file_subprocess_run(
                    tmpdir, per_file_shas=per_file_shas,
                    per_file_diffs=first_run_diffs,
                )
                update_project(project_dir, config_dir, fake_runner, fake_renderer)

            fake_runner.calls.clear()
            fake_renderer.calls.clear()

            second_run_diffs = {claude_md_relpath: "", settings_relpath: ""}
            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = per_file_subprocess_run(
                    tmpdir, per_file_shas=per_file_shas,
                    per_file_diffs=second_run_diffs,
                )
                update_project(project_dir, config_dir, fake_runner, fake_renderer)

            assert len(fake_runner.calls) == 0
            assert len(fake_renderer.calls) == 0

    def test_legacy_template_file_removed(self):
        legacy_path = os.path.join(
            _PROMPT_TEMPLATES_DIR, "update-project-claude-files.md",
        )
        assert not os.path.exists(legacy_path)

    def test_neither_new_template_mentions_sha_marker(self):
        import re
        sha_instruction_pattern = re.compile(
            r"(?i)write.*sha|update.*sha.*marker|update.*tracking.*comment",
        )
        for name in ("update-project-claude-md.md", "update-project-settings.md"):
            path = os.path.join(_PROMPT_TEMPLATES_DIR, name)
            with open(path) as f:
                content = f.read()
            assert "claude-config-files-sha" not in content, (
                f"{name} mentions claude-config-files-sha"
            )
            assert not sha_instruction_pattern.search(content), (
                f"{name} contains SHA-write instruction"
            )
