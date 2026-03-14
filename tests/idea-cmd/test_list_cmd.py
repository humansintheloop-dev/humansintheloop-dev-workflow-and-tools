"""Tests for i2code idea list --archived and --all flags."""

import os

import pytest
import yaml
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, name, location, state):
    """Create an idea in docs/ideas/<location>/<name>/ with a metadata file."""
    idea_dir = os.path.join(base, "docs", "ideas", location, name)
    os.makedirs(idea_dir, exist_ok=True)
    metadata_path = os.path.join(idea_dir, f"{name}-metadata.yaml")
    with open(metadata_path, "w") as f:
        yaml.safe_dump({"state": state}, f)
    return idea_dir


def _invoke(monkeypatch, tmp_path, extra_args=None):
    """Invoke `i2code idea list` and return the result."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    args = ["idea", "list"] + (extra_args or [])
    return runner.invoke(main, args)


def _names(result):
    """Extract idea names from list output."""
    return [line.split()[0] for line in result.output.strip().splitlines() if line.strip()]


@pytest.mark.unit
class TestListDefaultsToActive:

    def test_shows_active_ideas_only(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "active-one", "active", "draft")
        _create_idea(tmp_path, "archived-one", "archived", "completed")

        result = _invoke(monkeypatch, tmp_path)

        assert result.exit_code == 0
        assert _names(result) == ["active-one"]

    def test_state_filter_applies_to_active(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "wip-idea", "active", "wip")
        _create_idea(tmp_path, "draft-idea", "active", "draft")

        result = _invoke(monkeypatch, tmp_path, ["--state", "wip"])

        assert result.exit_code == 0
        assert _names(result) == ["wip-idea"]


@pytest.mark.unit
class TestListArchived:

    def test_shows_archived_ideas_only(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "active-one", "active", "draft")
        _create_idea(tmp_path, "archived-one", "archived", "completed")

        result = _invoke(monkeypatch, tmp_path, ["--archived"])

        assert result.exit_code == 0
        assert _names(result) == ["archived-one"]

    def test_state_filter_applies_to_archived(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "done-idea", "archived", "completed")
        _create_idea(tmp_path, "abandoned-idea", "archived", "abandoned")

        result = _invoke(monkeypatch, tmp_path, ["--archived", "--state", "completed"])

        assert result.exit_code == 0
        assert _names(result) == ["done-idea"]


@pytest.mark.unit
class TestListAll:

    def test_shows_both_active_and_archived(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "active-one", "active", "draft")
        _create_idea(tmp_path, "archived-one", "archived", "completed")

        result = _invoke(monkeypatch, tmp_path, ["--all"])

        assert result.exit_code == 0
        assert _names(result) == ["active-one", "archived-one"]

    def test_state_filter_applies_across_all(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "active-wip", "active", "wip")
        _create_idea(tmp_path, "archived-wip", "archived", "wip")
        _create_idea(tmp_path, "archived-done", "archived", "completed")

        result = _invoke(monkeypatch, tmp_path, ["--all", "--state", "wip"])

        assert result.exit_code == 0
        assert _names(result) == ["active-wip", "archived-wip"]


@pytest.mark.unit
class TestListMutuallyExclusive:

    def test_archived_and_all_are_mutually_exclusive(self, tmp_path, monkeypatch):
        result = _invoke(monkeypatch, tmp_path, ["--archived", "--all"])

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "mutually exclusive" in (result.output + str(result.exception)).lower()
