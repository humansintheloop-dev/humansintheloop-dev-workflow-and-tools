"""Tests for i2code.tracking.manage module — imperative tests for dry_run, capsys, and idempotent behavior."""

import os
import click
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


def _make_child_claude_sessions(project, child_name):
    """Create a child subdirectory with .claude/sessions containing a file."""
    sub_sessions = project / child_name / ".claude" / "sessions"
    sub_sessions.mkdir(parents=True)
    (sub_sessions / "file.md").write_text("data")
    return sub_sessions


def _make_child_hitl_with_correct_symlink(project, child_name):
    """Create a child .hitl/ with sessions symlinked to root .hitl/sessions."""
    sub_hitl = project / child_name / ".hitl"
    sub_hitl.mkdir(parents=True)
    rel_target = os.path.relpath(
        str(project / ".hitl" / "sessions"),
        str(sub_hitl),
    )
    os.symlink(rel_target, str(sub_hitl / "sessions"))
    return sub_hitl, rel_target


@pytest.mark.unit
class TestMigrateDryRun:
    def test_dry_run_does_not_change_files(self, project):
        _make_claude_dirs(project)
        _scan_and_migrate(project, dry_run=True)
        assert (project / ".claude" / "sessions" / "sample.md").exists()
        assert not (project / ".hitl").exists()
        content = (project / ".gitignore").read_text()
        assert "**/.claude/sessions" in content

    def test_migrates_symlink_dry_run(self, project):
        target = project / "external" / "sessions"
        target.mkdir(parents=True)
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        os.symlink(str(target), str(project / ".claude" / "sessions"))
        _scan_and_migrate(project, dry_run=True)
        assert os.path.islink(str(project / ".claude" / "sessions"))
        assert not (project / ".hitl" / "sessions").exists()

    def test_dry_run_skips_subdirectory_migration(self, project):
        """Dry run does not merge subdirectory files or create symlinks."""
        _make_claude_dirs(project)
        sub_sessions = _make_child_claude_sessions(project, "hooks")
        _scan_and_migrate(project, dry_run=True)
        assert not (project / ".hitl").exists()
        assert sub_sessions.exists()
        assert not (project / "hooks" / ".hitl").exists()

    def test_hitl_child_dry_run_skips_consolidation(self, project):
        """Dry run does not merge child .hitl/ files or create symlinks."""
        _make_claude_dirs(project)
        sub_hitl_sessions = project / "service" / ".hitl" / "sessions"
        sub_hitl_sessions.mkdir(parents=True)
        (sub_hitl_sessions / "file.md").write_text("data")
        _scan_and_migrate(project, dry_run=True)
        assert not (project / ".hitl").exists()
        assert sub_hitl_sessions.exists()
        assert (sub_hitl_sessions / "file.md").exists()


@pytest.mark.unit
class TestMigrateIdempotent:
    def test_skips_already_symlinked_subdirectory(self, project, capsys):
        """When SUBDIR/.hitl/sessions is already the correct symlink, skip it."""
        _make_claude_dirs(project)
        sub_hitl, rel_target = _make_child_hitl_with_correct_symlink(project, "hooks")
        _make_child_claude_sessions(project, "hooks")
        _scan_and_migrate(project)
        output = capsys.readouterr().out
        assert "already linked" in output
        assert os.readlink(str(sub_hitl / "sessions")) == rel_target

    def test_hitl_child_already_correct_symlink_skipped(self, project):
        """When child .hitl/sessions is already the correct symlink, skip it."""
        _make_claude_dirs(project)
        sub_hitl, rel_target = _make_child_hitl_with_correct_symlink(project, "service")
        (project / "service" / ".hitl" / "issues").mkdir(parents=True)
        (project / "service" / ".hitl" / "issues" / "f.md").write_text("data")
        _scan_and_migrate(project)
        assert os.path.islink(str(sub_hitl / "sessions"))
        assert os.readlink(str(sub_hitl / "sessions")) == rel_target

    def test_hitl_child_idempotent_second_run(self, project):
        """Running twice is idempotent — second run skips already-consolidated children."""
        _make_claude_dirs(project)
        sub_hitl_sessions = project / "service" / ".hitl" / "sessions"
        sub_hitl_sessions.mkdir(parents=True)
        (sub_hitl_sessions / "child.md").write_text("child data")
        _scan_and_migrate(project)
        _scan_and_migrate(project)
        assert (project / ".hitl" / "sessions" / "child.md").read_text() == "child data"
        sub_link = project / "service" / ".hitl" / "sessions"
        assert sub_link.is_symlink()

    def test_no_subdirectory_output_when_none_exist(self, project, capsys):
        """No subdirectory migration output when no subdirectories have .claude/."""
        _make_claude_dirs(project)
        _scan_and_migrate(project)
        output = capsys.readouterr().out
        assert "Symlink" not in output or "hooks" not in output


@pytest.mark.unit
class TestLinkEdgeCases:
    def test_raises_error_for_conflicting_symlink(self, project):
        (project / ".hitl").mkdir(parents=True)
        os.symlink("/old/target", str(project / ".hitl" / "sessions"))
        target_base = project / "tracking" / "my-project"
        with pytest.raises(click.ClickException) as exc_info:
            link_tracking(str(project), str(target_base))
        assert "/old/target" in exc_info.value.message
        assert "different directory" in exc_info.value.message

    def test_link_conflict_makes_no_changes(self, project):
        """When symlinks conflict, no filesystem modifications occur."""
        (project / ".hitl").mkdir(parents=True)
        os.symlink("/old/target/sessions", str(project / ".hitl" / "sessions"))
        os.symlink("/old/target/issues", str(project / ".hitl" / "issues"))
        target_base = project / "tracking" / "my-project"
        with pytest.raises(click.ClickException):
            link_tracking(str(project), str(target_base))
        assert os.readlink(str(project / ".hitl" / "sessions")) == "/old/target/sessions"
        assert os.readlink(str(project / ".hitl" / "issues")) == "/old/target/issues"
        assert not target_base.exists()

    def test_dry_run_does_not_change_files(self, project):
        target_base = project / "tracking" / "my-project"
        link_tracking(str(project), str(target_base), dry_run=True)
        assert not (project / ".hitl" / "sessions").exists()
        assert not (target_base / "sessions").exists()
