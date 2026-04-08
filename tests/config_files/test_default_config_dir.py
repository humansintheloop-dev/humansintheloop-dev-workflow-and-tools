import os

import pytest

from i2code.config_files import default_config_dir


@pytest.mark.unit
class TestDefaultConfigDir:
    def test_returns_string(self):
        result = default_config_dir()
        assert isinstance(result, str)

    def test_returns_existing_directory(self):
        result = default_config_dir()
        assert os.path.isdir(result)

    def test_contains_claude_md(self):
        result = default_config_dir()
        assert os.path.isfile(os.path.join(result, "CLAUDE.md"))

    def test_contains_settings_local_json(self):
        result = default_config_dir()
        assert os.path.isfile(os.path.join(result, "settings.local.json"))
