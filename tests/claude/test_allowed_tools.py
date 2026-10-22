"""Tests for claude command utilities."""

import pytest

from i2code.claude.erm import ERM_ROOT_ENV
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

    def test_grants_read_for_erm_root_instead_of_repo_root(self, tmp_path, monkeypatch):
        workspace = str(tmp_path)
        monkeypatch.setenv(ERM_ROOT_ENV, workspace)
        repo_root = str(tmp_path / "my-repo")
        idea_dir = str(tmp_path / "my-repo" / "docs" / "ideas" / "my-idea")

        result = build_allowed_tools_flag(repo_root, idea_dir)

        assert result == (
            f"Read(/{workspace}/**),"
            f"Edit(/{idea_dir}/**)"
        )


@pytest.mark.unit
class TestBuildReadOnlyToolsFlag:

    def test_builds_flag_with_read_only(self, tmp_path):
        repo_root = str(tmp_path / "my-repo")

        result = build_read_only_tools_flag(repo_root)

        assert result == f"Read(/{repo_root}/**)"

    def test_grants_read_for_erm_root_instead_of_repo_root(self, tmp_path, monkeypatch):
        workspace = str(tmp_path)
        monkeypatch.setenv(ERM_ROOT_ENV, workspace)

        result = build_read_only_tools_flag(str(tmp_path / "my-repo"))

        assert result == f"Read(/{workspace}/**)"
