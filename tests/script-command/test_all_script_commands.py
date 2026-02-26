import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"

# (cli_args, expected_script_name, expected_forwarded_args)
SCRIPT_COMMANDS = [
    # idea group — migrated to Python in tests/idea-cmd/test_brainstorm_cli.py
    # spec group — migrated to Python in tests/spec-cmd/test_spec_cli.py
    # design group
    pytest.param(
        ["design", "create", "my-dir"],
        "create-design-doc.sh",
        ["my-dir"],
        id="design-create",
    ),
    # setup group
    pytest.param(
        ["setup", "claude-files", "--config-dir", "/path/to/config-files"],
        "setup-claude-files.sh",
        ["--config-dir", "/path/to/config-files"],
        id="claude-files",
    ),
    pytest.param(
        ["setup", "claude-files", "--config-dir", "/path/to/config-files", "--extra-flag"],
        "setup-claude-files.sh",
        ["--config-dir", "/path/to/config-files", "--extra-flag"],
        id="claude-files-with-extra-flag",
    ),
    pytest.param(
        ["setup", "update-project", "my-project-dir", "--config-dir", "/path/to/config-files"],
        "update-project-claude-files.sh",
        ["my-project-dir", "--config-dir", "/path/to/config-files"],
        id="update-project",
    ),
    pytest.param(
        ["setup", "update-project", "my-project-dir", "--config-dir", "/path/to/config-files", "--", "--verbose"],
        "update-project-claude-files.sh",
        ["my-project-dir", "--config-dir", "/path/to/config-files", "--verbose"],
        id="update-project-with-separator",
    ),
    # plan group (script commands)
    pytest.param(
        ["plan", "create", "my-dir"],
        "make-plan.sh",
        ["my-dir"],
        id="plan-create",
    ),
    pytest.param(
        ["plan", "revise", "my-dir"],
        "revise-plan.sh",
        ["my-dir"],
        id="plan-revise",
    ),
    pytest.param(
        ["plan", "revise", "my-dir", "--feedback", "more detail"],
        "revise-plan.sh",
        ["my-dir", "--feedback", "more detail"],
        id="plan-revise-with-extra-args",
    ),
    # improve group
    pytest.param(
        ["improve", "analyze-sessions", "my-tracking-dir"],
        "analyze-sessions.sh",
        ["my-tracking-dir"],
        id="analyze-sessions",
    ),
    pytest.param(
        ["improve", "analyze-sessions", "dir1", "--verbose", "extra"],
        "analyze-sessions.sh",
        ["dir1", "--verbose", "extra"],
        id="analyze-sessions-with-extra-flags",
    ),
    pytest.param(
        ["improve", "summary-reports", "my-hitl-dir"],
        "create-summary-reports.sh",
        ["my-hitl-dir"],
        id="summary-reports",
    ),
    pytest.param(
        ["improve", "summary-reports", "my-hitl-dir", "--project-name", "my-project"],
        "create-summary-reports.sh",
        ["my-hitl-dir", "--project-name", "my-project"],
        id="summary-reports-with-project-name",
    ),
    pytest.param(
        ["improve", "review-issues", "my-hitl-dir"],
        "review-issues.sh",
        ["my-hitl-dir"],
        id="review-issues",
    ),
    pytest.param(
        ["improve", "review-issues", "my-hitl-dir", "--project", "my-project"],
        "review-issues.sh",
        ["my-hitl-dir", "--project", "my-project"],
        id="review-issues-with-extra-args",
    ),
    pytest.param(
        ["improve", "update-claude-files", "my-project-dir", "--config-dir", "/path/to/config-files"],
        "update-claude-files-from-project.sh",
        ["my-project-dir", "--config-dir", "/path/to/config-files"],
        id="update-claude-files",
    ),
    pytest.param(
        ["improve", "update-claude-files", "my-project-dir", "--config-dir", "/path/to/config-files", "--verbose"],
        "update-claude-files-from-project.sh",
        ["my-project-dir", "--config-dir", "/path/to/config-files", "--verbose"],
        id="update-claude-files-with-extra-flag",
    ),
]


@pytest.mark.parametrize("cli_args, expected_script, expected_args", SCRIPT_COMMANDS)
class TestScriptCommand:
    def test_invokes_correct_script_with_args(self, cli_args, expected_script, expected_args):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(main, cli_args)

            assert result.exit_code == 0
            mock_subprocess.run.assert_called_once()
            call_args = mock_subprocess.run.call_args[0][0]
            assert Path(call_args[0]) == SCRIPTS_DIR / expected_script
            assert call_args[1:] == expected_args

    def test_propagates_script_exit_code(self, cli_args, expected_script, expected_args):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(main, cli_args)

            assert result.exit_code == 42
