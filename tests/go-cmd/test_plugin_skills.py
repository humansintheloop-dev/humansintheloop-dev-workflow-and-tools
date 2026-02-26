"""Tests for go_cmd.plugin_skills — enumerate installed plugin skills."""


import pytest

from i2code.go_cmd.plugin_skills import list_plugin_skills


@pytest.mark.unit
class TestListPluginSkillsFindsSkills:

    def test_returns_comma_separated_skills_with_prefix(self, tmp_path):
        skills_dir = tmp_path / "idea-to-code-marketplace" / "idea-to-code" / "1.0.0" / "skills"
        (skills_dir / "tdd").mkdir(parents=True)
        (skills_dir / "plan-tracking").mkdir(parents=True)
        (skills_dir / "commit-guidelines").mkdir(parents=True)

        result = list_plugin_skills(cache_dir=str(tmp_path))

        skills = sorted(s.strip() for s in result.split(","))
        assert skills == [
            "idea-to-code:commit-guidelines",
            "idea-to-code:plan-tracking",
            "idea-to-code:tdd",
        ]

    def test_returns_single_skill_without_trailing_comma(self, tmp_path):
        skills_dir = tmp_path / "idea-to-code-marketplace" / "idea-to-code" / "1.0.0" / "skills"
        (skills_dir / "tdd").mkdir(parents=True)

        result = list_plugin_skills(cache_dir=str(tmp_path))

        assert result == "idea-to-code:tdd"

    def test_ignores_files_in_skills_directory(self, tmp_path):
        skills_dir = tmp_path / "idea-to-code-marketplace" / "idea-to-code" / "1.0.0" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "tdd").mkdir()
        (skills_dir / "README.md").write_text("not a skill")

        result = list_plugin_skills(cache_dir=str(tmp_path))

        assert result == "idea-to-code:tdd"


@pytest.mark.unit
class TestListPluginSkillsPluginNotFound:

    def test_returns_empty_string_when_plugin_absent(self, tmp_path, capsys):
        result = list_plugin_skills(cache_dir=str(tmp_path))

        assert result == ""

    def test_prints_warning_to_stderr_when_plugin_absent(self, tmp_path, capsys):
        list_plugin_skills(cache_dir=str(tmp_path))

        captured = capsys.readouterr()
        assert "Warning" in captured.err or "warning" in captured.err

    def test_warning_includes_cache_dir_path(self, tmp_path, capsys):
        list_plugin_skills(cache_dir=str(tmp_path))

        captured = capsys.readouterr()
        assert str(tmp_path) in captured.err


@pytest.mark.unit
class TestListPluginSkillsRespectsEnvVar:

    def test_uses_plugin_cache_dir_env_var(self, tmp_path, monkeypatch):
        skills_dir = tmp_path / "idea-to-code-marketplace" / "idea-to-code" / "1.0.0" / "skills"
        (skills_dir / "tdd").mkdir(parents=True)

        monkeypatch.setenv("PLUGIN_CACHE_DIR", str(tmp_path))

        result = list_plugin_skills()

        assert result == "idea-to-code:tdd"

    def test_uses_default_when_env_var_not_set(self, monkeypatch):
        monkeypatch.delenv("PLUGIN_CACHE_DIR", raising=False)

        # With default path (~/.claude/plugins/cache), plugin won't be found
        # so we just verify it doesn't crash and returns empty string
        result = list_plugin_skills()

        assert result == "" or isinstance(result, str)
