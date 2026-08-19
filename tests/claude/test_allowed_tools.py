"""Tests for claude command utilities."""

import pytest

from i2code.claude.permissions import build_allowed_tools_flag, build_read_only_tools_flag


@pytest.mark.unit
class TestBuildAllowedToolsFlag:

    def test_builds_flag_with_read_and_edit(self, tmp_path):
        repo_root = str(tmp_path / "my-repo")
        idea_dir = str(tmp_path / "my-repo" / "docs" / "ideas" / "my-idea")

        result = build_allowed_tools_flag(repo_root, idea_dir)

        assert result == (
            f"Read(/{repo_root}/**),"
            f"Edit(/{idea_dir}/**)"
        )

    def test_omits_path_scoped_write_rule(self, tmp_path):
        """Write(path) rules are ignored by Claude Code; Edit(path) covers all file-editing tools."""
        repo_root = str(tmp_path / "my-repo")
        idea_dir = str(tmp_path / "my-repo" / "docs" / "ideas" / "my-idea")

        result = build_allowed_tools_flag(repo_root, idea_dir)

        assert "Write(" not in result


@pytest.mark.unit
class TestBuildReadOnlyToolsFlag:

    def test_builds_flag_with_read_only(self, tmp_path):
        repo_root = str(tmp_path / "my-repo")

        result = build_read_only_tools_flag(repo_root)

        assert result == f"Read(/{repo_root}/**)"
