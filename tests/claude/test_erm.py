"""Unit tests for locating and recording the ERM workspace root."""

import os

import click
import pytest

from i2code.claude.erm import ERM_ROOT_ENV, erm_root, find_erm_root, use_erm_root


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "workspace"
    (root / ".erm").mkdir(parents=True)
    (root / "project" / "src").mkdir(parents=True)
    return root.resolve()


@pytest.mark.unit
class TestFindErmRoot:

    def test_finds_ancestor_containing_erm_directory(self, workspace):
        assert find_erm_root(workspace / "project" / "src") == workspace

    def test_raises_click_exception_when_no_ancestor_has_erm_directory(self, tmp_path):
        with pytest.raises(click.ClickException, match="No .erm directory found above"):
            find_erm_root(tmp_path)


@pytest.mark.unit
class TestUseErmRoot:

    def test_records_erm_root_in_environment(self, workspace):
        use_erm_root(workspace / "project" / "src")

        assert os.environ[ERM_ROOT_ENV] == str(workspace)


@pytest.mark.unit
class TestErmRoot:

    def test_returns_recorded_root(self, workspace):
        use_erm_root(workspace)

        assert erm_root() == str(workspace)

    def test_returns_none_when_not_recorded(self):
        assert erm_root() is None
