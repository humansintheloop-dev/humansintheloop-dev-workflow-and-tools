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

# Absolute path to the project root (two levels up from tests/issue/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Plugin directory containing .claude-plugin/plugin.json
PLUGIN_DIR = PROJECT_ROOT / "claude-code-plugins" / "idea-to-code"


@pytest.mark.integration_claude
class TestIssueReportEndToEnd:
    """Runs `claude -p` to invoke /claude-issue-report and verifies the created file."""

    VALID_CATEGORIES = {"rule-violation", "improvement", "confusion"}

    @pytest.fixture()
    def issue_dir(self, tmp_path):
        """Create a temp git repo with .hitl/issues/active/ directory."""
        active_dir = tmp_path / ".hitl" / "issues" / "active"
        active_dir.mkdir(parents=True)

        # Initialize a git repo (required for claude to operate)
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
        )

        return tmp_path

    @pytest.fixture()
    def created_issue(self, issue_dir):
        """Run claude -p to create an issue report and return (active_dir, md_files, result)."""
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
            cwd=issue_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        active_dir = issue_dir / ".hitl" / "issues" / "active"
        md_files = list(active_dir.glob("*.md"))

        return active_dir, md_files, result

    def test_claude_exits_successfully(self, created_issue):
        _, _, result = created_issue
        assert result.returncode == 0, (
            f"claude exited with {result.returncode}\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )

    def test_exactly_one_issue_file_created(self, created_issue):
        _, md_files, _ = created_issue
        assert len(md_files) == 1, f"Expected 1 .md file, found {len(md_files)}"

    def test_valid_yaml_frontmatter_with_status_active(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        frontmatter = self._parse_frontmatter(content)

        assert frontmatter is not None, "No YAML frontmatter found"
        assert frontmatter.get("status") == "active"

    def test_valid_category_in_frontmatter(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        frontmatter = self._parse_frontmatter(content)

        assert frontmatter is not None, "No YAML frontmatter found"
        assert frontmatter.get("category") in self.VALID_CATEGORIES, (
            f"category '{frontmatter.get('category')}' not in {self.VALID_CATEGORIES}"
        )

    def test_contains_5_whys_analysis_section(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        assert "## 5 Whys Analysis" in content

    def test_contains_context_section(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        assert "## Context (Last 5 Messages)" in content

    def test_contains_suggested_improvement_section(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        assert "## Suggested improvement" in content

    def test_contains_resolution_section(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        assert "## Resolution" in content

    @pytest.mark.xfail(
        reason="PreToolUse hooks loaded via --plugin-dir do not receive session_id "
        "in claude -p mode. Hook logic is verified by unit tests in "
        "issue-session-injector.test.js. In normal interactive use, the hook "
        "receives session_id and injects it correctly.",
        strict=False,
    )
    def test_session_id_is_not_unknown(self, created_issue):
        _, md_files, _ = created_issue
        content = md_files[0].read_text()
        frontmatter = self._parse_frontmatter(content)

        assert frontmatter is not None, "No YAML frontmatter found"
        session_id = frontmatter.get("claude_session_id")
        assert session_id is not None, "claude_session_id not found in frontmatter"
        assert session_id != "unknown", "claude_session_id should not be 'unknown' — hook should inject it"

    @staticmethod
    def _parse_frontmatter(content):
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return None
        end = content.index("---", 3)
        return yaml.safe_load(content[3:end])
