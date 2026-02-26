import stat
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from i2code.script_runner import run_script


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"


class TestRunScriptResolvesPath:
    def test_resolves_to_scripts_directory(self):
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("make-plan.sh")

            called_path = Path(mock_subprocess.run.call_args[0][0][0])
            assert called_path == SCRIPTS_DIR / "make-plan.sh"


class TestRunScriptEnsuresExecutability:
    def test_sets_execute_permission(self, tmp_path):
        script = tmp_path / "test-script.sh"
        script.write_text("#!/bin/bash\nexit 0\n")
        script.chmod(0o644)

        with patch("i2code.script_runner.SCRIPTS_DIR", tmp_path):
            with patch("i2code.script_runner.subprocess") as mock_subprocess:
                mock_subprocess.run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0
                )
                run_script("test-script.sh")

                mode = script.stat().st_mode
                assert mode & stat.S_IXUSR, "Script should have user execute permission"


class TestRunScriptForwardsArguments:
    def test_forwards_arguments_to_subprocess(self):
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            run_script("make-plan.sh", ["my-dir"])

            call_args = mock_subprocess.run.call_args[0][0]
            assert call_args[1:] == ["my-dir"]


class TestRunScriptReturnsResult:
    def test_returns_completed_process(self):
        expected = subprocess.CompletedProcess(args=[], returncode=42)
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = expected
            result = run_script("make-plan.sh")
            assert result is expected


class TestRunScriptRaisesForMissingScript:
    def test_raises_file_not_found_error(self):
        with pytest.raises(FileNotFoundError, match="no-such-script.sh"):
            run_script("no-such-script.sh")
