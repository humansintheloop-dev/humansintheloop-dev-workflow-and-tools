"""Unit tests for the directories `i2code --add-dir` gives Claude access to."""

import pytest

from i2code.claude.added_dirs import added_dirs, use_added_dirs


@pytest.mark.unit
class TestAddedDirs:

    def test_no_directories_when_add_dir_not_used(self):
        assert added_dirs() == []

    def test_returns_directories_as_absolute_paths(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        use_added_dirs(["dir1", "/abs/dir2"])

        assert added_dirs() == [str(tmp_path.resolve() / "dir1"), "/abs/dir2"]
