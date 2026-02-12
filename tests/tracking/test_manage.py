"""Tests for i2code.tracking.manage module."""

import os
import pytest

from i2code.tracking.manage import migrate, link


@pytest.fixture
def project(tmp_path):
    """Create a minimal project directory."""
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("**/.claude/sessions\n**/.claude/issues\n")
    return tmp_path


def _make_claude_dirs(project):
    """Create .claude/issues and .claude/sessions with sample files."""
    for subdir in ("issues/active", "sessions"):
        d = project / ".claude" / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / "sample.md").write_text("sample")


class TestMigrate:
    def test_moves_directories(self, project):
        _make_claude_dirs(project)
        migrate(str(project))
        assert (project / ".hitl" / "sessions" / "sample.md").exists()
        assert (project / ".hitl" / "issues" / "active" / "sample.md").exists()
        assert not (project / ".claude" / "sessions").exists()
        assert not (project / ".claude" / "issues").exists()

    def test_updates_gitignore(self, project):
        _make_claude_dirs(project)
        migrate(str(project))
        content = (project / ".gitignore").read_text()
        assert "**/.hitl" in content
        assert ".claude/sessions" not in content
        assert ".claude/issues" not in content

    def test_dry_run_does_not_change_files(self, project):
        _make_claude_dirs(project)
        migrate(str(project), dry_run=True)
        assert (project / ".claude" / "sessions" / "sample.md").exists()
        assert not (project / ".hitl").exists()
        content = (project / ".gitignore").read_text()
        assert "**/.claude/sessions" in content

    def test_skips_when_nothing_to_migrate(self, project):
        # No .claude/issues or .claude/sessions
        migrate(str(project))  # should not raise

    def test_migrates_symlink_to_hitl(self, project):
        """When .claude/sessions is a symlink, recreate it at .hitl/sessions and remove the old one."""
        target = project / "external" / "sessions"
        target.mkdir(parents=True)
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(project / ".claude" / "sessions"))
        migrate(str(project))
        # .claude/sessions symlink removed
        assert not os.path.exists(str(project / ".claude" / "sessions"))
        # .hitl/sessions is now a symlink to the same target
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target)

    def test_migrates_symlink_merges_hitl_directory(self, project):
        """When .claude/sessions is a symlink and .hitl/sessions is a directory,
        move directory contents to symlink target, replace with symlink."""
        target = project / "external" / "sessions"
        target.mkdir(parents=True)
        (target / "old.md").write_text("from target")
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(project / ".claude" / "sessions"))
        # Also have a real .hitl/sessions directory with files
        (project / ".hitl" / "sessions").mkdir(parents=True)
        (project / ".hitl" / "sessions" / "local.md").write_text("local data")
        migrate(str(project))
        # local.md moved to target
        assert (target / "local.md").read_text() == "local data"
        # old.md still there
        assert (target / "old.md").read_text() == "from target"
        # .hitl/sessions is now a symlink
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target)
        # .claude/sessions removed
        assert not os.path.exists(str(project / ".claude" / "sessions"))

    def test_migrates_symlink_dry_run(self, project):
        target = project / "external" / "sessions"
        target.mkdir(parents=True)
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(project / ".claude" / "sessions"))
        migrate(str(project), dry_run=True)
        # Nothing changed
        assert os.path.islink(str(project / ".claude" / "sessions"))
        assert not (project / ".hitl" / "sessions").exists()

    def test_skips_when_destination_exists(self, project):
        _make_claude_dirs(project)
        (project / ".hitl" / "sessions").mkdir(parents=True)
        (project / ".hitl" / "sessions" / "existing.md").write_text("keep")
        migrate(str(project))
        # sessions not moved because destination exists
        assert (project / ".claude" / "sessions" / "sample.md").exists()
        assert (project / ".hitl" / "sessions" / "existing.md").exists()


    def test_warns_about_stale_subdirectories(self, project, capsys):
        """Warn when subdirectories have .claude/sessions or .claude/issues."""
        _make_claude_dirs(project)
        # Create a stale subdirectory like hooks/.claude/sessions
        stale = project / "hooks" / ".claude" / "sessions"
        stale.mkdir(parents=True)
        (stale / "old-session.md").write_text("stale")
        migrate(str(project))
        output = capsys.readouterr().out
        assert "hooks/.claude/sessions" in output
        assert "no longer gitignored" in output

    def test_no_warning_when_no_stale_subdirectories(self, project, capsys):
        _make_claude_dirs(project)
        migrate(str(project))
        output = capsys.readouterr().out
        assert "no longer gitignored" not in output


class TestLink:
    def test_creates_symlinks(self, project):
        target_base = project / "tracking" / "my-project"
        link(str(project), str(target_base))
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.path.islink(str(project / ".hitl" / "issues"))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")
        assert os.readlink(str(project / ".hitl" / "issues")) == str(target_base / "issues")

    def test_creates_target_directories(self, project):
        target_base = project / "tracking" / "my-project"
        link(str(project), str(target_base))
        assert (target_base / "sessions").is_dir()
        assert (target_base / "issues").is_dir()

    def test_moves_existing_files_to_target(self, project):
        (project / ".hitl" / "sessions").mkdir(parents=True)
        (project / ".hitl" / "sessions" / "old.md").write_text("old data")
        target_base = project / "tracking" / "my-project"
        link(str(project), str(target_base))
        assert (target_base / "sessions" / "old.md").read_text() == "old data"
        assert os.path.islink(str(project / ".hitl" / "sessions"))

    def test_replaces_incorrect_symlink(self, project):
        (project / ".hitl").mkdir(parents=True)
        os.symlink("/old/target", str(project / ".hitl" / "sessions"))
        target_base = project / "tracking" / "my-project"
        link(str(project), str(target_base))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")

    def test_skips_correct_symlink(self, project):
        target_base = project / "tracking" / "my-project"
        (target_base / "sessions").mkdir(parents=True)
        (target_base / "issues").mkdir(parents=True)
        (project / ".hitl").mkdir(parents=True)
        os.symlink(str(target_base / "sessions"), str(project / ".hitl" / "sessions"))
        os.symlink(str(target_base / "issues"), str(project / ".hitl" / "issues"))
        link(str(project), str(target_base))  # should not raise
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")

    def test_dry_run_does_not_change_files(self, project):
        target_base = project / "tracking" / "my-project"
        link(str(project), str(target_base), dry_run=True)
        assert not (project / ".hitl" / "sessions").exists()
        assert not (target_base / "sessions").exists()


class TestMigrateAndLink:
    def test_migrate_then_link(self, project):
        _make_claude_dirs(project)
        target_base = project / "tracking" / "my-project"
        migrate(str(project))
        link(str(project), str(target_base))
        # Files should end up in target
        assert (target_base / "sessions" / "sample.md").exists()
        assert (target_base / "issues" / "active" / "sample.md").exists()
        # .hitl dirs should be symlinks
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.path.islink(str(project / ".hitl" / "issues"))
