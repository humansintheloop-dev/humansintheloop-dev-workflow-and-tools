"""End-to-end test: skill -> hook -> CLI -> file.

Requires `claude` CLI on PATH and a valid API key.
Excluded from fast CI runs via the `integration_claude` marker.
"""

import os
import subprocess
import uuid
from pathlib import Path

import pytest
import yaml

from i2code.issue import VALID_CATEGORIES

# Absolute path to the project root (two levels up from tests/issue/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Plugin directory containing .claude-plugin/plugin.json
PLUGIN_DIR = PROJECT_ROOT / "claude-code-plugins" / "idea-to-code"


@pytest.mark.integration_claude
def test_claude_issue_report_creates_valid_issue(tmp_path):
    """Invoke claude once and verify return code, issue count, and file format."""
    # Set up a temp git repo with .hitl/issues/active/
    active_dir = tmp_path / ".hitl" / "issues" / "active"
    active_dir.mkdir(parents=True)

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
             "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
    )

    # Run claude -p to create an issue report
    session_id = str(uuid.uuid4())
    result = subprocess.run(
        [
            "claude", "-p",
            "/claude-issue-report Test issue: the commit message used wrong format",
            "--plugin-dir", str(PLUGIN_DIR),
            "--allowedTools", "Bash", "Read", "Glob", "Grep",
            "--permission-mode", "bypassPermissions",
            "--session-id", session_id,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Assert: claude exits successfully
    assert result.returncode == 0, (
        f"claude exited with {result.returncode}\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )

    # Assert: exactly one issue file created
    md_files = list(active_dir.glob("*.md"))
    assert len(md_files) == 1, f"Expected 1 .md file, found {len(md_files)}"

    content = md_files[0].read_text()

    # Assert: valid YAML frontmatter
    assert content.startswith("---"), "No YAML frontmatter found"
    end = content.index("---", 3)
    frontmatter = yaml.safe_load(content[3:end])
    assert frontmatter is not None, "YAML frontmatter is empty"

    # Assert: frontmatter fields
    assert frontmatter.get("status") == "active"
    assert frontmatter.get("category") in VALID_CATEGORIES, (
        f"category '{frontmatter.get('category')}' not in {VALID_CATEGORIES}"
    )

    # Assert: required sections
    assert "## 5 Whys Analysis" in content
    assert "## Context (Last 5 Messages)" in content
    assert "## Suggested improvement" in content
    assert "## Resolution" in content
