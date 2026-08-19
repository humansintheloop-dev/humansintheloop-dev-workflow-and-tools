"""Tests for Claude permissions and settings setup."""

import json
import os
import tempfile
import pytest
from i2code.claude.permissions import (
    calculate_claude_permissions,
    copy_source_settings,
    ensure_claude_permissions,
    REQUIRED_PERMISSIONS,
)


@pytest.mark.unit
class TestCalculateClaudePermissions:
    """Test calculation of Claude permissions for --allowedTools."""

    def test_includes_required_permissions(self):
        perms = calculate_claude_permissions("/fake/repo")

        for req in REQUIRED_PERMISSIONS:
            assert req in perms

    def test_includes_edit_for_repo_root(self):
        perms = calculate_claude_permissions("/fake/repo")

        assert "Edit(//fake/repo/**)" in perms

    def test_omits_path_scoped_write_rule(self):
        """Write(path) rules are ignored by Claude Code; Edit(path) covers all file-editing tools."""
        perms = calculate_claude_permissions("/fake/repo")

        assert not any(perm.startswith("Write(") for perm in perms)


def _read_allow_rules(path):
    with open(path, "r") as f:
        return json.load(f)["permissions"]["allow"]


def _write_settings(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def _read_settings(path):
    with open(path, "r") as f:
        return f.read()


@pytest.fixture
def settings_paths():
    with tempfile.TemporaryDirectory() as tmpdir:
        source_root = os.path.join(tmpdir, "source")
        dest_root = os.path.join(tmpdir, "dest")
        os.makedirs(source_root)
        os.makedirs(dest_root)
        source_settings = os.path.join(source_root, ".claude", "settings.local.json")
        dest_settings = os.path.join(dest_root, ".claude", "settings.local.json")
        yield source_root, dest_root, source_settings, dest_settings


@pytest.mark.unit
class TestCopySourceSettings:
    """Test copy_source_settings copies .claude/settings.local.json from source to dest."""

    def test_copies_settings_when_source_root_provided(self, settings_paths):
        """Should copy .claude/settings.local.json from source to dest."""
        source_root, dest_root, source_settings, dest_settings = settings_paths
        _write_settings(source_settings, '{"permissions": {"allow": ["Bash(*)"]}}')

        copy_source_settings(dest_root, source_root=source_root)

        assert os.path.isfile(dest_settings)
        assert '"permissions"' in _read_settings(dest_settings)

    def test_skips_settings_when_no_source_root(self, settings_paths):
        """Should not copy settings when source_root is None."""
        _, dest_root, _, dest_settings = settings_paths

        copy_source_settings(dest_root)

        assert not os.path.exists(dest_settings)

    def test_skips_settings_when_missing_in_source(self, settings_paths):
        """Should not fail if .claude/settings.local.json does not exist in source."""
        source_root, dest_root, _, dest_settings = settings_paths

        copy_source_settings(dest_root, source_root=source_root)

        assert not os.path.exists(dest_settings)


@pytest.mark.unit
class TestEnsureClaudePermissions:
    """Test that settings.local.json is kept free of rules Claude Code cannot match."""

    def test_drops_stale_path_scoped_write_rules(self, settings_paths):
        """Write(path) rules left over from earlier versions are removed, not preserved."""
        _, dest_root, _, dest_settings = settings_paths
        _write_settings(dest_settings, json.dumps(
            {"permissions": {"allow": ["Write(//old/repo/**)", "Bash(ls:*)"]}}
        ))

        ensure_claude_permissions(dest_root)

        allow = _read_allow_rules(dest_settings)
        assert "Write(//old/repo/**)" not in allow
        assert "Bash(ls:*)" in allow

    def test_keeps_bare_write_tool_rule(self, settings_paths):
        """A bare Write rule (no path) is still a valid tool-level permission."""
        _, dest_root, _, dest_settings = settings_paths
        _write_settings(dest_settings, json.dumps({"permissions": {"allow": ["Write"]}}))

        ensure_claude_permissions(dest_root)

        assert "Write" in _read_allow_rules(dest_settings)
