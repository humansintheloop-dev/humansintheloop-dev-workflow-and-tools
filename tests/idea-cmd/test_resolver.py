"""Tests for idea resolver scanning active/ and archived/ with metadata files."""

import warnings
from pathlib import Path

import pytest
import yaml

from i2code.idea.resolver import IdeaInfo, list_ideas, resolve_idea


def _create_idea(git_root: Path, location: str, name: str, state: str) -> Path:
    """Create an idea directory with metadata file.

    Args:
        git_root: Root of the git repository.
        location: Either 'active' or 'archived'.
        name: Idea name.
        state: Lifecycle state to write in metadata.
    """
    idea_dir = git_root / "docs" / "ideas" / location / name
    idea_dir.mkdir(parents=True)
    metadata_path = idea_dir / f"{name}-metadata.yaml"
    with open(metadata_path, "w") as f:
        yaml.safe_dump({"state": state}, f)
    return idea_dir


@pytest.mark.unit
class TestResolveIdeaFromActive:
    def test_resolves_idea_in_active_directory(self, tmp_path):
        _create_idea(tmp_path, "active", "my-feature", "wip")

        result = resolve_idea("my-feature", tmp_path)

        assert result == IdeaInfo(
            name="my-feature",
            state="wip",
            directory="docs/ideas/active/my-feature",
        )


@pytest.mark.unit
class TestResolveIdeaFromArchived:
    def test_resolves_idea_in_archived_directory(self, tmp_path):
        _create_idea(tmp_path, "archived", "old-feature", "completed")

        result = resolve_idea("old-feature", tmp_path)

        assert result == IdeaInfo(
            name="old-feature",
            state="completed",
            directory="docs/ideas/archived/old-feature",
        )


@pytest.mark.unit
class TestResolveIdeaNotFound:
    def test_raises_error_when_idea_not_found(self, tmp_path):
        (tmp_path / "docs" / "ideas" / "active").mkdir(parents=True)

        with pytest.raises(ValueError, match="Idea not found: nonexistent"):
            resolve_idea("nonexistent", tmp_path)


@pytest.mark.unit
class TestListIdeasActiveOnly:
    def test_lists_only_active_ideas_by_default(self, tmp_path):
        _create_idea(tmp_path, "active", "feature-a", "draft")
        _create_idea(tmp_path, "active", "feature-b", "wip")
        _create_idea(tmp_path, "archived", "old-idea", "completed")

        result = list_ideas(tmp_path)

        assert len(result) == 2
        names = [idea.name for idea in result]
        assert "feature-a" in names
        assert "feature-b" in names
        assert "old-idea" not in names


@pytest.mark.unit
class TestListIdeasWithArchived:
    def test_lists_active_and_archived_when_requested(self, tmp_path):
        _create_idea(tmp_path, "active", "feature-a", "draft")
        _create_idea(tmp_path, "archived", "old-idea", "completed")

        result = list_ideas(tmp_path, include_archived=True)

        assert len(result) == 2
        names = [idea.name for idea in result]
        assert "feature-a" in names
        assert "old-idea" in names


@pytest.mark.unit
class TestMissingMetadataFile:
    def test_warns_when_metadata_file_missing(self, tmp_path):
        idea_dir = tmp_path / "docs" / "ideas" / "active" / "no-meta"
        idea_dir.mkdir(parents=True)
        # No metadata file created

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = list_ideas(tmp_path)

        assert len(result) == 1
        assert result[0].name == "no-meta"
        assert result[0].state == "unknown"
        assert len(w) == 1
        assert "metadata" in str(w[0].message).lower()
