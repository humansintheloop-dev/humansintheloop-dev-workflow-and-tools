import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"

# (cli_args, expected_script_name, expected_forwarded_args)
SCRIPT_COMMANDS = [
    # idea-to-plan group
    pytest.param(
        ["idea-to-plan", "brainstorm", "my-dir"],
        "brainstorm-idea.sh",
        ["my-dir"],
        id="brainstorm",
    ),
    pytest.param(
        ["idea-to-plan", "spec", "my-dir"],
        "make-spec.sh",
        ["my-dir"],
        id="spec",
    ),
    pytest.param(
        ["idea-to-plan", "revise-spec", "my-dir"],
        "revise-spec.sh",
        ["my-dir"],
        id="revise-spec",
    ),
    pytest.param(
        ["idea-to-plan", "revise-plan", "my-dir"],
        "revise-plan.sh",
        ["my-dir"],
        id="revise-plan",
    ),
    pytest.param(
        ["idea-to-plan", "make-plan", "my-dir"],
        "make-plan.sh",
        ["my-dir"],
        id="make-plan",
    ),
    pytest.param(
        ["idea-to-plan", "design-doc", "my-dir"],
        "create-design-doc.sh",
        ["my-dir"],
        id="design-doc",
    ),
    pytest.param(
        ["idea-to-plan", "run", "my-dir"],
        "idea-to-code.sh",
        ["my-dir"],
        id="run",
    ),
    pytest.param(
        ["idea-to-plan", "run", "my-dir", "--verbose", "extra"],
        "idea-to-code.sh",
        ["my-dir", "--verbose", "extra"],
        id="run-with-extra-flags",
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
