"""Tests for i2code issue create CLI command."""

import json
import os
import re

import pytest
from click.testing import CliRunner

from i2code.cli import main


VALID_INPUT = {
    "description": "Test issue",
    "category": "rule-violation",
    "analysis": "## 5 Whys Analysis\n\n1. Why?",
    "context": "## Context (Last 5 Messages)\n\nUser: test",
    "suggestion": "Add a rule",
}


def _invoke_create(tmp_path, input_data=None, args=None):
    """Invoke `i2code issue create` via CliRunner with stdin and tmp_path as cwd."""
    active_dir = tmp_path / ".hitl" / "issues" / "active"
    active_dir.mkdir(parents=True, exist_ok=True)

    if input_data is None:
        input_data = VALID_INPUT

    runner = CliRunner()
    cli_args = ["issue", "create"]
    if args:
        cli_args.extend(args)

    return runner.invoke(
        main,
        cli_args,
        input=json.dumps(input_data),
        env={"I2CODE_PROJECT_ROOT": str(tmp_path)},
    )


@pytest.mark.unit
class TestIssueCreateHappyPath:

    def test_exits_zero_on_valid_input(self, tmp_path):
        result = _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        assert result.exit_code == 0, f"stderr: {result.output}"

    def test_creates_file_in_active_directory(self, tmp_path):
        _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        md_files = list(active_dir.glob("*.md"))
        assert len(md_files) == 1

    def test_filename_matches_timestamp_pattern(self, tmp_path):
        _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        md_files = list(active_dir.glob("*.md"))
        assert re.match(r"\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.md", md_files[0].name)

    def test_frontmatter_has_correct_fields(self, tmp_path):
        _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        content = list(active_dir.glob("*.md"))[0].read_text()

        assert "id:" in content
        assert "created:" in content
        assert "status: active" in content
        assert "category: rule-violation" in content
        assert "claude_session_id: test-session-123" in content

    def test_content_sections_present(self, tmp_path):
        _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        content = list(active_dir.glob("*.md"))[0].read_text()

        assert "# Test issue" in content
        assert "## 5 Whys Analysis" in content
        assert "## Context (Last 5 Messages)" in content
        assert "## Suggested improvement" in content
        assert "## Resolution" in content

    def test_stdout_contains_absolute_path(self, tmp_path):
        result = _invoke_create(tmp_path, args=["--session-id", "test-session-123"])
        output = result.output.strip()
        assert output.startswith("/")
        assert output.endswith(".md")
        assert os.path.isfile(output)


@pytest.mark.unit
class TestIssueCreateMissingSessionId:

    def test_missing_session_id_defaults_to_unknown(self, tmp_path):
        result = _invoke_create(tmp_path)
        assert result.exit_code == 0
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        content = list(active_dir.glob("*.md"))[0].read_text()
        assert "claude_session_id: unknown" in content
