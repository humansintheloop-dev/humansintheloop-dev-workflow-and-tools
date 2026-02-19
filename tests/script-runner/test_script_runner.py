import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from i2code.script_runner import run_script


class TestRunScriptResolvesPath:
    def test_resolves_path_to_bundled_script(self):
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("brainstorm-idea.sh")

            called_args = mock_subprocess.run.call_args[0][0]
            resolved_path = Path(called_args[0])
            assert resolved_path.name == "brainstorm-idea.sh"
            assert resolved_path.parent.name == "scripts"


class TestRunScriptEnsuresExecutability:
    def test_sets_execute_permission(self):
        with (
            patch("i2code.script_runner.subprocess") as mock_subprocess,
            patch("i2code.script_runner.os.chmod") as mock_chmod,
        ):
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("brainstorm-idea.sh")

            mock_chmod.assert_called_once()
            path_arg, mode_arg = mock_chmod.call_args[0]
            assert Path(path_arg).name == "brainstorm-idea.sh"
            assert mode_arg & 0o111  # execute bits set


class TestRunScriptForwardsArguments:
    def test_forwards_arguments_to_subprocess(self):
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("brainstorm-idea.sh", ["my-dir"])

            called_args = mock_subprocess.run.call_args[0][0]
            assert called_args[1:] == ["my-dir"]

    def test_forwards_multiple_arguments(self):
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("brainstorm-idea.sh", ["arg1", "arg2", "arg3"])

            called_args = mock_subprocess.run.call_args[0][0]
            assert called_args[1:] == ["arg1", "arg2", "arg3"]


class TestRunScriptReturnsResult:
    def test_returns_completed_process(self):
        expected = subprocess.CompletedProcess(args=[], returncode=42)
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = expected
            result = run_script("brainstorm-idea.sh")

            assert result is expected
            assert result.returncode == 42


class TestRunScriptMissingScript:
    def test_raises_file_not_found_error_for_missing_script(self):
        with pytest.raises(FileNotFoundError, match="nonexistent.sh"):
            run_script("nonexistent.sh")
