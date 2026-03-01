"""Unit tests for idea_resolver module."""

import os

import pytest

from i2code.idea.resolver import IdeaInfo, list_ideas, resolve_idea


def _create_idea(base, state, name):
    """Create an idea directory under docs/ideas/{state}/{name}/."""
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    return idea_dir


@pytest.mark.unit
class TestListIdeasMultipleStates:

    def test_returns_ideas_sorted_alphabetically(self, tmp_path):
        _create_idea(tmp_path, "wip", "zebra")
        _create_idea(tmp_path, "draft", "alpha")
        _create_idea(tmp_path, "ready", "middle")

        result = list_ideas(tmp_path)

        assert [idea.name for idea in result] == ["alpha", "middle", "zebra"]

    def test_returns_correct_state_for_each_idea(self, tmp_path):
        _create_idea(tmp_path, "wip", "zebra")
        _create_idea(tmp_path, "draft", "alpha")

        result = list_ideas(tmp_path)

        assert result[0] == IdeaInfo(
            name="alpha", state="draft", directory="docs/ideas/draft/alpha"
        )
        assert result[1] == IdeaInfo(
            name="zebra", state="wip", directory="docs/ideas/wip/zebra"
        )


@pytest.mark.unit
class TestListIdeasEmpty:

    def test_returns_empty_list_when_no_ideas(self, tmp_path):
        os.makedirs(tmp_path / "docs" / "ideas" / "draft")
        assert list_ideas(tmp_path) == []

    def test_returns_empty_list_when_ideas_dir_missing(self, tmp_path):
        assert list_ideas(tmp_path) == []


@pytest.mark.unit
class TestListIdeasMissingStateDirectories:

    def test_skips_missing_state_directories(self, tmp_path):
        _create_idea(tmp_path, "draft", "only-idea")
        # Other state directories (ready, wip, etc.) don't exist

        result = list_ideas(tmp_path)

        assert len(result) == 1
        assert result[0].name == "only-idea"


@pytest.mark.unit
class TestResolveIdeaSingleMatch:

    def test_returns_correct_idea_info(self, tmp_path):
        _create_idea(tmp_path, "wip", "my-feature")

        result = resolve_idea("my-feature", tmp_path)

        assert result == IdeaInfo(
            name="my-feature",
            state="wip",
            directory="docs/ideas/wip/my-feature",
        )


@pytest.mark.unit
class TestResolveIdeaNoMatch:

    def test_raises_error_with_idea_name(self, tmp_path):
        os.makedirs(tmp_path / "docs" / "ideas" / "draft")

        with pytest.raises(ValueError, match="no-such-idea"):
            resolve_idea("no-such-idea", tmp_path)


@pytest.mark.unit
class TestResolveIdeaMultipleMatches:

    def test_raises_error_listing_conflicting_states(self, tmp_path):
        _create_idea(tmp_path, "draft", "duplicated")
        _create_idea(tmp_path, "wip", "duplicated")

        with pytest.raises(ValueError, match="draft"):
            resolve_idea("duplicated", tmp_path)
