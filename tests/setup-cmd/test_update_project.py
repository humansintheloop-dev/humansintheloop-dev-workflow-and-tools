"""Tests for update_project: validates directories, extracts SHA from CLAUDE.md,
generates git diff, handles first sync (no previous SHA), template variables correct,
Claude invoked interactively."""

import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project


def _create_project_dir(tmpdir, *, claude_md_content=None):
    """Create a project directory, optionally with CLAUDE.md."""
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    if claude_md_content is not None:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write(claude_md_content)
    return project_dir


def _create_config_dir(tmpdir):
    """Create a config directory."""
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    return config_dir


def _fake_subprocess_run(repo_root, current_sha="abc123def", diff_output="diff content"):
    """Create a mock for subprocess.run that handles git commands."""
    def mock_run(cmd, capture_output=False, text=False, check=False, cwd=None):
        cmd_str = " ".join(cmd)
        result = subprocess.CompletedProcess(cmd, 0)
        if "rev-parse --show-toplevel" in cmd_str:
            result.stdout = repo_root + "\n"
        elif "log -1 --format=%H" in cmd_str:
            result.stdout = current_sha + "\n"
        elif "diff" in cmd_str:
            result.stdout = diff_output + "\n"
        else:
            result.stdout = ""
        result.stderr = ""
        return result
    return mock_run


def _run_with_mocked_git(fakes, tmpdir, *, claude_md_content=None, current_sha="abc123def"):
    """Set up dirs, mock subprocess, call update_project, return (project_dir, config_dir).

    Args:
        fakes: tuple of (fake_runner, fake_renderer)
    """
    fake_runner, fake_renderer = fakes
    project_dir = _create_project_dir(tmpdir, claude_md_content=claude_md_content)
    config_dir = _create_config_dir(tmpdir)
    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = _fake_subprocess_run(tmpdir, current_sha=current_sha)
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return project_dir, config_dir


@pytest.mark.unit
class TestValidation:

    def test_raises_when_project_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = _create_config_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project("/nonexistent/project", config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_config_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project(project_dir, "/nonexistent/config", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestShaExtraction:

    def test_extracts_previous_sha_from_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git(
                (fake_runner, fake_renderer), tmpdir,
                claude_md_content="# Project\n<!-- claude-config-files-sha: abc123def456 -->\n",
                current_sha="e99999",
            )
            _, variables = fake_renderer.calls[0]
            assert variables["PREVIOUS_SHA"] == "abc123def456"

    def test_previous_sha_empty_when_no_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["PREVIOUS_SHA"] == ""

    def test_previous_sha_empty_when_no_marker_in_claude_md(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git(
                (fake_runner, fake_renderer), tmpdir,
                claude_md_content="# Project\nNo SHA here\n",
            )
            _, variables = fake_renderer.calls[0]
            assert variables["PREVIOUS_SHA"] == ""


@pytest.mark.unit
class TestGitOperations:

    def test_derives_repo_root_from_config_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            calls = []

            def tracking_run(cmd, capture_output=False, text=False, check=False, cwd=None):
                calls.append((cmd, cwd))
                return _fake_subprocess_run(tmpdir)(
                    cmd, capture_output=capture_output, text=text, check=check, cwd=cwd,
                )

            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = tracking_run
                update_project(project_dir, config_dir, fake_runner, fake_renderer)

            rev_parse_calls = [c for c in calls if "rev-parse" in " ".join(c[0])]
            assert len(rev_parse_calls) == 1
            assert rev_parse_calls[0][1] == config_dir

    def test_gets_current_sha_of_config_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git(
                (fake_runner, fake_renderer), tmpdir, current_sha="ccc999",
            )
            _, variables = fake_renderer.calls[0]
            assert variables["CURRENT_SHA"] == "ccc999"

    def test_generates_diff_between_previous_and_current_sha(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(
                tmpdir,
                claude_md_content="# Project\n<!-- claude-config-files-sha: aaa111 -->\n",
            )
            config_dir = _create_config_dir(tmpdir)

            calls = []

            def tracking_run(cmd, capture_output=False, text=False, check=False, cwd=None):
                calls.append(cmd)
                return _fake_subprocess_run(tmpdir, current_sha="bbb222", diff_output="diff here")(
                    cmd, capture_output=capture_output, text=text, check=check, cwd=cwd,
                )

            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = tracking_run
                update_project(project_dir, config_dir, fake_runner, fake_renderer)

            diff_calls = [c for c in calls if "diff" in " ".join(c)]
            assert len(diff_calls) == 1
            assert "aaa111..bbb222" in " ".join(diff_calls[0])

    def test_diff_message_when_no_previous_sha(self, fake_runner, fake_renderer):
        """First sync: no previous SHA produces informational message instead of diff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert "first sync" in variables["CONFIG_DIFF"].lower()

    def test_handles_repo_root_not_found(self, fake_runner, fake_renderer):
        """When git rev-parse fails, current SHA and diff are empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            def failing_run(cmd, capture_output=False, text=False, check=False, cwd=None):
                cmd_str = " ".join(cmd)
                if "rev-parse" in cmd_str:
                    result = subprocess.CompletedProcess(cmd, 128)
                    result.stdout = ""
                    result.stderr = "fatal: not a git repository"
                    return result
                return _fake_subprocess_run(tmpdir)(
                    cmd, capture_output=capture_output, text=text, check=check, cwd=cwd,
                )

            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = failing_run
                update_project(project_dir, config_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["CURRENT_SHA"] == ""


@pytest.mark.unit
class TestTemplateRendering:

    def test_renders_update_project_claude_files_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            template_name, _ = fake_renderer.calls[0]
            assert template_name == "update-project-claude-files.md"

    def test_template_receives_project_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, _ = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["PROJECT_DIR"] == project_dir

    def test_template_receives_all_eight_variables(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            expected_keys = {
                "PROJECT_DIR", "PROJECT_CLAUDE_MD", "PROJECT_SETTINGS",
                "CONFIG_CLAUDE_MD", "CONFIG_SETTINGS",
                "CURRENT_SHA", "PREVIOUS_SHA", "CONFIG_DIFF",
            }
            assert set(variables.keys()) == expected_keys

    def test_template_receives_project_claude_md_path(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, _ = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["PROJECT_CLAUDE_MD"] == os.path.join(project_dir, "CLAUDE.md")

    def test_template_receives_project_settings_path(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, _ = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["PROJECT_SETTINGS"] == os.path.join(project_dir, ".claude", "settings.local.json")

    def test_template_receives_config_claude_md_path(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, config_dir = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["CONFIG_CLAUDE_MD"] == os.path.join(config_dir, "CLAUDE.md")

    def test_template_receives_config_settings_path(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _, config_dir = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, variables = fake_renderer.calls[0]
            assert variables["CONFIG_SETTINGS"] == os.path.join(config_dir, "settings.local.json")


@pytest.mark.unit
class TestClaudeInvocation:

    def test_invokes_claude_interactively(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            method, _, _ = fake_runner.calls[0]
            assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, cmd, _ = fake_runner.calls[0]
            assert cmd[0] == "claude"

    def test_claude_receives_rendered_prompt(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, cmd, _ = fake_runner.calls[0]
            assert "template=update-project-claude-files.md" in cmd[1]

    def test_claude_runs_in_project_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir, _ = _run_with_mocked_git((fake_runner, fake_renderer), tmpdir)
            _, _, cwd = fake_runner.calls[0]
            assert cwd == project_dir

    def test_returns_claude_result(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(tmpdir)
            config_dir = _create_config_dir(tmpdir)

            fake_runner.set_result(ClaudeResult(returncode=0))
            with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
                mock_sub.run = _fake_subprocess_run(tmpdir)
                result = update_project(project_dir, config_dir, fake_runner, fake_renderer)

            assert result.returncode == 0
