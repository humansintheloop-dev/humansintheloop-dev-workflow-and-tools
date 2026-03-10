"""Tests for claude command utilities."""

import pytest

from i2code.claude_cmd import build_allowed_tools_flag


@pytest.mark.unit
class TestBuildAllowedToolsFlag:

    def test_builds_flag_with_read_write_edit(self):
        repo_root = "/home/user/my-repo"
        idea_dir = "/home/user/my-repo/docs/ideas/my-idea"

        result = build_allowed_tools_flag(repo_root, idea_dir)

        assert result == (
            "Read(/home/user/my-repo/),"
            "Write(/home/user/my-repo/docs/ideas/my-idea/),"
            "Edit(/home/user/my-repo/docs/ideas/my-idea/)"
        )
