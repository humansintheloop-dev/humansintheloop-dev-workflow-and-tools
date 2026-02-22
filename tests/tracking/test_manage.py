"""Tests for i2code.tracking.manage module."""

import os
import pytest

from i2code.tracking.manage import migrate_tracking, link_tracking
from i2code.tracking.model import TrackedWorkingDirectory


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


def _scan_and_migrate(project, dry_run=False):
    """Scan project and run migration."""
    twd = TrackedWorkingDirectory.scan(project)
    migrate_tracking(twd, dry_run=dry_run)


@pytest.mark.unit
class TestMigrate:
    def test_moves_directories(self, project):
        _make_claude_dirs(project)
        _scan_and_migrate(project)
        assert (project / ".hitl" / "sessions" / "sample.md").exists()
        assert (project / ".hitl" / "issues" / "active" / "sample.md").exists()
        assert not (project / ".claude" / "sessions").exists()
        assert not (project / ".claude" / "issues").exists()

    def test_updates_gitignore(self, project):
        _make_claude_dirs(project)
        _scan_and_migrate(project)
        content = (project / ".gitignore").read_text()
        assert "**/.hitl" in content
        assert ".claude/sessions" not in content
        assert ".claude/issues" not in content

    def test_dry_run_does_not_change_files(self, project):
        _make_claude_dirs(project)
        _scan_and_migrate(project, dry_run=True)
        assert (project / ".claude" / "sessions" / "sample.md").exists()
        assert not (project / ".hitl").exists()
        content = (project / ".gitignore").read_text()
        assert "**/.claude/sessions" in content

    def test_skips_when_nothing_to_migrate(self, project):
        # No .claude/issues or .claude/sessions
        _scan_and_migrate(project)  # should not raise

    def test_migrates_symlink_to_hitl(self, project):
        """When .claude/sessions is a symlink, recreate it at .hitl/sessions and remove the old one."""
        target = project / "external" / "sessions"
        target.mkdir(parents=True)
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(project / ".claude" / "sessions"))
        _scan_and_migrate(project)
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
        _scan_and_migrate(project)
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
        _scan_and_migrate(project, dry_run=True)
        # Nothing changed
        assert os.path.islink(str(project / ".claude" / "sessions"))
        assert not (project / ".hitl" / "sessions").exists()

    def test_merges_when_destination_exists(self, project):
        """When .hitl already exists and .claude/{sessions,issues} have files,
        merge files into .hitl and remove .claude/{sessions,issues}."""
        _make_claude_dirs(project)
        (project / ".hitl" / "sessions").mkdir(parents=True)
        (project / ".hitl" / "sessions" / "existing.md").write_text("keep")
        (project / ".hitl" / "issues" / "active").mkdir(parents=True)
        (project / ".claude" / "sessions" / "debug.log").write_text("debug stuff")
        _scan_and_migrate(project)
        # session files merged into .hitl
        assert (project / ".hitl" / "sessions" / "sample.md").exists()
        assert (project / ".hitl" / "sessions" / "existing.md").read_text() == "keep"
        # debug.log not moved
        assert not (project / ".hitl" / "sessions" / "debug.log").exists()
        # issue files merged into .hitl
        assert (project / ".hitl" / "issues" / "active" / "sample.md").exists()
        # .claude/{sessions,issues} removed
        assert not (project / ".claude" / "sessions").exists()
        assert not (project / ".claude" / "issues").exists()


    def test_migrates_subdirectory_sessions(self, project):
        """Subdirectory .claude/sessions files merge into root .hitl/sessions,
        debug.log excluded, and SUBDIR/.hitl/sessions becomes symlink to root."""
        _make_claude_dirs(project)
        # Create a subdirectory with .claude/sessions
        sub_sessions = project / "hooks" / ".claude" / "sessions"
        sub_sessions.mkdir(parents=True)
        (sub_sessions / "old-session.md").write_text("stale")
        (sub_sessions / "debug.log").write_text("debug stuff")
        _scan_and_migrate(project)
        # Subdirectory file merged into root .hitl/sessions
        assert (project / ".hitl" / "sessions" / "old-session.md").read_text() == "stale"
        # debug.log not merged
        assert not (project / ".hitl" / "sessions" / "debug.log").exists()
        # Subdirectory .claude/sessions removed
        assert not sub_sessions.exists()
        # hooks/.hitl/sessions is a symlink to root .hitl/sessions
        sub_hitl = project / "hooks" / ".hitl" / "sessions"
        assert sub_hitl.is_symlink()
        link_target = os.path.relpath(
            str(project / ".hitl" / "sessions"),
            str(project / "hooks" / ".hitl"),
        )
        assert os.readlink(str(sub_hitl)) == link_target

    def test_skips_already_symlinked_subdirectory(self, project, capsys):
        """When SUBDIR/.hitl/sessions is already the correct symlink, skip it."""
        _make_claude_dirs(project)
        # Pre-create the correct symlink
        sub_hitl = project / "hooks" / ".hitl"
        sub_hitl.mkdir(parents=True)
        rel_target = os.path.relpath(
            str(project / ".hitl" / "sessions"),
            str(sub_hitl),
        )
        os.symlink(rel_target, str(sub_hitl / "sessions"))
        # Also create a subdirectory .claude/sessions to trigger discovery
        sub_sessions = project / "hooks" / ".claude" / "sessions"
        sub_sessions.mkdir(parents=True)
        (sub_sessions / "file.md").write_text("data")
        _scan_and_migrate(project)
        output = capsys.readouterr().out
        assert "already linked" in output
        # Symlink unchanged
        assert os.readlink(str(sub_hitl / "sessions")) == rel_target

    def test_dry_run_skips_subdirectory_migration(self, project):
        """Dry run does not merge subdirectory files or create symlinks."""
        _make_claude_dirs(project)
        sub_sessions = project / "hooks" / ".claude" / "sessions"
        sub_sessions.mkdir(parents=True)
        (sub_sessions / "file.md").write_text("data")
        _scan_and_migrate(project, dry_run=True)
        # File not merged
        assert not (project / ".hitl").exists()
        # Subdirectory still intact
        assert sub_sessions.exists()
        # No symlink created
        assert not (project / "hooks" / ".hitl").exists()

    def test_migrates_multiple_subdirectories(self, project):
        """Multiple subdirectories all merge into root .hitl/ and get symlinks."""
        _make_claude_dirs(project)
        for name in ("app-a", "app-b"):
            d = project / name / ".claude" / "sessions"
            d.mkdir(parents=True)
            (d / f"{name}.md").write_text(name)
        _scan_and_migrate(project)
        # Both files merged into root
        assert (project / ".hitl" / "sessions" / "app-a.md").read_text() == "app-a"
        assert (project / ".hitl" / "sessions" / "app-b.md").read_text() == "app-b"
        # Both get symlinks
        for name in ("app-a", "app-b"):
            sub_hitl = project / name / ".hitl" / "sessions"
            assert sub_hitl.is_symlink()

    def test_subdirectory_conflict_keeps_root_version(self, project):
        """When root .hitl/ already has a file with the same name, root wins."""
        _make_claude_dirs(project)
        sub_sessions = project / "hooks" / ".claude" / "sessions"
        sub_sessions.mkdir(parents=True)
        (sub_sessions / "sample.md").write_text("from subdirectory")
        _scan_and_migrate(project)
        # Root .claude/sessions/sample.md was moved first, so root version wins
        assert (project / ".hitl" / "sessions" / "sample.md").read_text() == "sample"

    def test_migrates_subdirectory_issues(self, project):
        """Handles issues/ subdirectory, not just sessions/."""
        _make_claude_dirs(project)
        sub_issues = project / "hooks" / ".claude" / "issues"
        sub_issues.mkdir(parents=True)
        (sub_issues / "bug.md").write_text("bug report")
        _scan_and_migrate(project)
        assert (project / ".hitl" / "issues" / "bug.md").read_text() == "bug report"
        assert not sub_issues.exists()
        sub_hitl = project / "hooks" / ".hitl" / "issues"
        assert sub_hitl.is_symlink()

    def test_no_subdirectory_output_when_none_exist(self, project, capsys):
        """No subdirectory migration output when no subdirectories have .claude/."""
        _make_claude_dirs(project)
        _scan_and_migrate(project)
        output = capsys.readouterr().out
        assert "Symlink" not in output or "hooks" not in output


@pytest.mark.unit
class TestLink:
    def test_creates_symlinks(self, project):
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base))
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.path.islink(str(project / ".hitl" / "issues"))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")
        assert os.readlink(str(project / ".hitl" / "issues")) == str(target_base / "issues")

    def test_creates_target_directories(self, project):
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base))
        assert (target_base / "sessions").is_dir()
        assert (target_base / "issues").is_dir()

    def test_moves_existing_files_to_target(self, project):
        (project / ".hitl" / "sessions").mkdir(parents=True)
        (project / ".hitl" / "sessions" / "old.md").write_text("old data")
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base))
        assert (target_base / "sessions" / "old.md").read_text() == "old data"
        assert os.path.islink(str(project / ".hitl" / "sessions"))

    def test_replaces_incorrect_symlink(self, project):
        (project / ".hitl").mkdir(parents=True)
        os.symlink("/old/target", str(project / ".hitl" / "sessions"))
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base))
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")

    def test_skips_correct_symlink(self, project):
        target_base = project / "tracking" / "my-project"
        (target_base / "sessions").mkdir(parents=True)
        (target_base / "issues").mkdir(parents=True)
        (project / ".hitl").mkdir(parents=True)
        os.symlink(str(target_base / "sessions"), str(project / ".hitl" / "sessions"))
        os.symlink(str(target_base / "issues"), str(project / ".hitl" / "issues"))
        link_tracking(str(project), str(target_base))  # should not raise
        assert os.readlink(str(project / ".hitl" / "sessions")) == str(target_base / "sessions")

    def test_dry_run_does_not_change_files(self, project):
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base), dry_run=True)
        assert not (project / ".hitl" / "sessions").exists()
        assert not (target_base / "sessions").exists()


@pytest.mark.unit
class TestMigrateAndLink:
    def test_migrate_then_link(self, project):
        _make_claude_dirs(project)
        target_base = project / "tracking" / "my-project"
        _scan_and_migrate(project)
        link_tracking(str(project), str(target_base))
        # Files should end up in target
        assert (target_base / "sessions" / "sample.md").exists()
        assert (target_base / "issues" / "active" / "sample.md").exists()
        # .hitl dirs should be symlinks
        assert os.path.islink(str(project / ".hitl" / "sessions"))
        assert os.path.islink(str(project / ".hitl" / "issues"))
