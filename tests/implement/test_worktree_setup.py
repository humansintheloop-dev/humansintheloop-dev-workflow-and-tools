"""Tests for worktree project setup: settings copy, setup script."""

import os
import tempfile
import pytest

from i2code.implement.worktree_setup import setup_project


@pytest.mark.unit
class TestSetupProject:
    """Test setup_project copies settings and runs setup script."""

    def test_copies_settings_local_json(self):
        """Should copy .claude/settings.local.json from source to dest."""

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source")
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(source)
            os.makedirs(dest)

            # Create .claude/settings.local.json in source
            claude_dir = os.path.join(source, ".claude")
            os.makedirs(claude_dir)
            settings_file = os.path.join(claude_dir, "settings.local.json")
            with open(settings_file, "w") as f:
                f.write('{"permissions": {"allow": ["Bash(*)"]}}')

            setup_project(source, dest)

            dest_settings = os.path.join(dest, ".claude", "settings.local.json")
            assert os.path.isfile(dest_settings)
            with open(dest_settings, "r") as f:
                content = f.read()
            assert '"permissions"' in content

    def test_skips_settings_when_missing(self):
        """Should not fail if .claude/settings.local.json does not exist."""

        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "source")
            dest = os.path.join(tmpdir, "dest")
            os.makedirs(source)
            os.makedirs(dest)

            setup_project(source, dest)

            assert not os.path.exists(os.path.join(dest, ".claude", "settings.local.json"))
