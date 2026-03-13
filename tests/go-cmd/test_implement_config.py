"""Tests for go_cmd.implement_config — config read/write, prompting, flags, labels."""


import pytest

from conftest import TempIdeaProject


def _write_config_file(project, interactive, trunk, isolation_type="none"):
    """Write implement config and return the config file path."""
    from i2code.go_cmd.implement_config import write_implement_config

    path = project.implement_config_file
    write_implement_config(path, interactive=interactive, isolation_type=isolation_type, trunk=trunk)
    return path


@pytest.mark.unit
class TestWriteAndReadConfigRoundTrip:

    @pytest.mark.parametrize("interactive,trunk", [
        (True, False),
        (False, True),
    ])
    def test_write_then_read_preserves_config(self, interactive, trunk):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            path = _write_config_file(project, interactive, trunk)
            config = read_implement_config(path)
            assert config["interactive"] is interactive
            assert config["trunk"] is trunk


@pytest.mark.unit
class TestReadConfigMissingFile:

    def test_read_returns_none_when_file_missing(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            result = read_implement_config(project.implement_config_file)
            assert result is None


@pytest.mark.unit
class TestReadConfigDefaults:

    def test_missing_interactive_defaults_to_true(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            path = project.implement_config_file
            with open(path, "w") as f:
                f.write("trunk: true\n")
            config = read_implement_config(path)
            assert config["interactive"] is True
            assert config["trunk"] is True

    def test_missing_trunk_defaults_to_false(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            path = project.implement_config_file
            with open(path, "w") as f:
                f.write("interactive: false\n")
            config = read_implement_config(path)
            assert config["interactive"] is False
            assert config["trunk"] is False


@pytest.mark.unit
class TestReadConfigIsolationType:

    def test_read_config_with_isolation_type(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            path = project.implement_config_file
            with open(path, "w") as f:
                f.write("interactive: true\n")
                f.write("isolation_type: nono\n")
                f.write("trunk: false\n")
            config = read_implement_config(path)
            assert config["interactive"] is True
            assert config["isolation_type"] == "nono"
            assert config["trunk"] is False

    def test_legacy_config_missing_isolation_type_defaults_to_none(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            path = project.implement_config_file
            with open(path, "w") as f:
                f.write("interactive: true\n")
                f.write("trunk: false\n")
            config = read_implement_config(path)
            assert config["isolation_type"] == "none"


@pytest.mark.unit
class TestWriteConfigIsolationType:

    def test_write_then_read_preserves_isolation_type(self):
        from i2code.go_cmd.implement_config import read_implement_config, write_implement_config

        with TempIdeaProject("my-feature") as project:
            path = project.implement_config_file
            write_implement_config(path, interactive=True, isolation_type="nono", trunk=False)
            config = read_implement_config(path)
            assert config["isolation_type"] == "nono"


@pytest.mark.unit
class TestPromptImplementConfig:

    def test_interactive_mode_and_worktree_branch(self):
        from i2code.go_cmd.implement_config import prompt_implement_config

        choices = iter(["1", "1"])
        interactive, trunk = prompt_implement_config(
            menu_fn=lambda prompt, default, options: int(next(choices))
        )
        assert interactive is True
        assert trunk is False

    def test_non_interactive_mode_and_trunk_branch(self):
        from i2code.go_cmd.implement_config import prompt_implement_config

        choices = iter(["2", "2"])
        interactive, trunk = prompt_implement_config(
            menu_fn=lambda prompt, default, options: int(next(choices))
        )
        assert interactive is False
        assert trunk is True


@pytest.mark.unit
class TestBuildImplementFlags:

    def test_interactive_worktree_returns_empty(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        flags = build_implement_flags({"interactive": True, "trunk": False})
        assert flags == []

    def test_non_interactive_adds_flag(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        flags = build_implement_flags({"interactive": False, "trunk": False})
        assert "--non-interactive" in flags

    def test_trunk_adds_flag(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        flags = build_implement_flags({"interactive": True, "trunk": True})
        assert "--trunk" in flags

    def test_non_interactive_and_trunk_adds_both_flags(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        flags = build_implement_flags({"interactive": False, "trunk": True})
        assert "--non-interactive" in flags
        assert "--trunk" in flags

    def test_isolation_type_nono_produces_flag(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        config = {"interactive": True, "isolation_type": "nono", "trunk": False}
        flags = build_implement_flags(config)
        assert "--isolation-type" in flags
        assert "nono" in flags

    def test_isolation_type_none_omits_flag(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        config = {"interactive": True, "isolation_type": "none", "trunk": False}
        flags = build_implement_flags(config)
        assert "--isolation-type" not in flags

    def test_non_interactive_and_container_isolation_produces_both_flags(self):
        from i2code.go_cmd.implement_config import build_implement_flags

        config = {"interactive": False, "isolation_type": "container", "trunk": False}
        flags = build_implement_flags(config)
        assert "--non-interactive" in flags
        assert "--isolation-type" in flags
        assert "container" in flags


@pytest.mark.unit
class TestBuildImplementLabel:

    def test_label_with_no_config_file(self):
        from i2code.go_cmd.implement_config import build_implement_label

        with TempIdeaProject("my-feature") as project:
            label = build_implement_label(project.implement_config_file)
            assert label == "Implement the entire plan: i2code implement"

    @pytest.mark.parametrize("interactive,trunk,expected_suffix", [
        (False, True, " --non-interactive --trunk"),
        (True, False, ""),
    ])
    def test_label_with_config(self, interactive, trunk, expected_suffix):
        from i2code.go_cmd.implement_config import build_implement_label

        with TempIdeaProject("my-feature") as project:
            _write_config_file(project, interactive, trunk)
            label = build_implement_label(project.implement_config_file)
            expected = f"Implement the entire plan: i2code implement{expected_suffix}"
            assert label == expected
