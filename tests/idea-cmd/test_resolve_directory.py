"""Tests for resolve_idea_directory."""

from unittest.mock import patch

import pytest

from i2code.idea.resolver import IdeaInfo, resolve_idea_directory


@pytest.mark.unit
class TestResolveIdeaDirectory:

    def test_bare_name_maps_to_active_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        idea_dir = tmp_path / "docs" / "ideas" / "active" / "foo"
        idea_dir.mkdir(parents=True)

        result = resolve_idea_directory("foo")

        assert result == str(idea_dir)

    def test_path_with_slash_returned_as_is(self, tmp_path):
        result = resolve_idea_directory("bar/baz")

        assert result == "bar/baz"

    def test_bare_name_not_existing_returns_path_anyway(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = resolve_idea_directory("foo")

        assert result.endswith("docs/ideas/active/foo")

    @patch("i2code.idea.resolver.resolve_idea")
    def test_with_resolve_finds_existing_idea(self, mock_resolve, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_resolve.return_value = IdeaInfo(
            name="foo", state="wip", directory="docs/ideas/active/foo",
        )

        result = resolve_idea_directory("foo", resolve=True)

        assert result.endswith("docs/ideas/active/foo")
        mock_resolve.assert_called_once()

    @patch("i2code.idea.resolver.resolve_idea")
    def test_with_resolve_falls_back_to_active_when_not_found(self, mock_resolve, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_resolve.side_effect = ValueError("Idea not found: foo")

        result = resolve_idea_directory("foo", resolve=True)

        assert result.endswith("docs/ideas/active/foo")

    @patch("i2code.idea.resolver.resolve_idea")
    def test_with_resolve_raises_on_ambiguous(self, mock_resolve, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        mock_resolve.side_effect = ValueError("Idea 'foo' found in multiple states: ready, wip")

        with pytest.raises(ValueError, match="multiple states"):
            resolve_idea_directory("foo", resolve=True)

    def test_dot_relative_path_returned_as_is(self):
        result = resolve_idea_directory("./some-dir")

        assert result == "./some-dir"
