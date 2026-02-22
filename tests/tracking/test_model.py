"""Tests for i2code.tracking.model domain classes."""

import os
import pytest

from i2code.tracking.model import (
    TrackingDir,
    LegacyTracking,
    HitlTracking,
    TrackedDirectory,
    TrackedWorkingDirectory,
)


@pytest.mark.unit
class TestTrackingDir:
    def test_exists_when_directory_present(self, tmp_path):
        d = tmp_path / "sessions"
        d.mkdir()
        td = TrackingDir(d)
        assert td.exists is True

    def test_exists_when_directory_absent(self, tmp_path):
        td = TrackingDir(tmp_path / "sessions")
        assert td.exists is False

    def test_is_symlink_when_symlink(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "sessions"
        os.symlink(str(target), str(link))
        td = TrackingDir(link)
        assert td.is_symlink is True

    def test_is_symlink_when_real_directory(self, tmp_path):
        d = tmp_path / "sessions"
        d.mkdir()
        td = TrackingDir(d)
        assert td.is_symlink is False

    def test_is_symlink_when_absent(self, tmp_path):
        td = TrackingDir(tmp_path / "sessions")
        assert td.is_symlink is False

    def test_symlink_target(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "sessions"
        os.symlink(str(target), str(link))
        td = TrackingDir(link)
        assert td.symlink_target == str(target)

    def test_symlink_target_none_when_not_symlink(self, tmp_path):
        d = tmp_path / "sessions"
        d.mkdir()
        td = TrackingDir(d)
        assert td.symlink_target is None

    def test_list_files_returns_file_names(self, tmp_path):
        d = tmp_path / "sessions"
        d.mkdir()
        (d / "a.md").write_text("a")
        (d / "b.md").write_text("b")
        td = TrackingDir(d)
        assert sorted(td.list_files()) == ["a.md", "b.md"]

    def test_list_files_empty_directory(self, tmp_path):
        d = tmp_path / "sessions"
        d.mkdir()
        td = TrackingDir(d)
        assert td.list_files() == []

    def test_list_files_absent_directory(self, tmp_path):
        td = TrackingDir(tmp_path / "sessions")
        assert td.list_files() == []

    def test_migrate_to_moves_contents(self, tmp_path):
        src = tmp_path / "src_sessions"
        src.mkdir()
        (src / "file.md").write_text("content")
        dst = tmp_path / "dst_sessions"
        dst.mkdir()
        src_td = TrackingDir(src)
        dst_td = TrackingDir(dst)
        src_td.migrate_to(dst_td)
        assert (dst / "file.md").read_text() == "content"
        assert not (src / "file.md").exists()

    def test_migrate_to_skips_existing_files_in_target(self, tmp_path):
        src = tmp_path / "src_sessions"
        src.mkdir()
        (src / "file.md").write_text("from source")
        dst = tmp_path / "dst_sessions"
        dst.mkdir()
        (dst / "file.md").write_text("from target")
        src_td = TrackingDir(src)
        dst_td = TrackingDir(dst)
        src_td.migrate_to(dst_td)
        assert (dst / "file.md").read_text() == "from target"

    def test_path_attribute(self, tmp_path):
        d = tmp_path / "sessions"
        td = TrackingDir(d)
        assert td.path == d


@pytest.mark.unit
class TestLegacyTracking:
    def test_constructed_from_base_path(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "sessions").mkdir()
        (claude_dir / "issues").mkdir()
        lt = LegacyTracking(claude_dir)
        assert lt.sessions.path == claude_dir / "sessions"
        assert lt.issues.path == claude_dir / "issues"

    def test_sessions_and_issues_are_tracking_dirs(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        lt = LegacyTracking(claude_dir)
        assert isinstance(lt.sessions, TrackingDir)
        assert isinstance(lt.issues, TrackingDir)

    def test_base_path_attribute(self, tmp_path):
        claude_dir = tmp_path / ".claude"
        lt = LegacyTracking(claude_dir)
        assert lt.base_path == claude_dir


@pytest.mark.unit
class TestHitlTracking:
    def test_constructed_from_base_path(self, tmp_path):
        hitl_dir = tmp_path / ".hitl"
        hitl_dir.mkdir()
        (hitl_dir / "sessions").mkdir()
        (hitl_dir / "issues").mkdir()
        ht = HitlTracking(hitl_dir)
        assert ht.sessions.path == hitl_dir / "sessions"
        assert ht.issues.path == hitl_dir / "issues"

    def test_sessions_and_issues_are_tracking_dirs(self, tmp_path):
        hitl_dir = tmp_path / ".hitl"
        ht = HitlTracking(hitl_dir)
        assert isinstance(ht.sessions, TrackingDir)
        assert isinstance(ht.issues, TrackingDir)

    def test_base_path_attribute(self, tmp_path):
        hitl_dir = tmp_path / ".hitl"
        ht = HitlTracking(hitl_dir)
        assert ht.base_path == hitl_dir


@pytest.mark.unit
class TestTrackedDirectory:
    def test_from_path_with_both_claude_and_hitl(self, tmp_path):
        (tmp_path / ".claude" / "sessions").mkdir(parents=True)
        (tmp_path / ".hitl" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is not None
        assert td.hitl is not None

    def test_from_path_with_only_claude(self, tmp_path):
        (tmp_path / ".claude" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is not None
        assert td.hitl is None

    def test_from_path_with_only_hitl(self, tmp_path):
        (tmp_path / ".hitl" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is None
        assert td.hitl is not None

    def test_from_path_with_neither(self, tmp_path):
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is None
        assert td.hitl is None

    def test_status_none_when_no_tracking(self, tmp_path):
        td = TrackedDirectory.from_path(tmp_path)
        assert td.status == "none"

    def test_status_legacy_only(self, tmp_path):
        (tmp_path / ".claude" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.status == "legacy"

    def test_status_hitl_only(self, tmp_path):
        (tmp_path / ".hitl" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.status == "hitl"

    def test_status_both(self, tmp_path):
        (tmp_path / ".claude" / "sessions").mkdir(parents=True)
        (tmp_path / ".hitl" / "sessions").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.status == "both"

    def test_path_attribute(self, tmp_path):
        td = TrackedDirectory.from_path(tmp_path)
        assert td.path == tmp_path

    def test_legacy_detected_when_sessions_or_issues_exist(self, tmp_path):
        (tmp_path / ".claude" / "issues").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is not None
        assert td.status == "legacy"

    def test_hitl_detected_when_sessions_or_issues_exist(self, tmp_path):
        (tmp_path / ".hitl" / "issues").mkdir(parents=True)
        td = TrackedDirectory.from_path(tmp_path)
        assert td.hitl is not None
        assert td.status == "hitl"

    def test_claude_dir_without_sessions_or_issues_is_not_legacy(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        td = TrackedDirectory.from_path(tmp_path)
        assert td.legacy is None
        assert td.status == "none"


@pytest.mark.unit
class TestTrackedWorkingDirectory:
    def test_root_is_tracked_directory(self, tmp_path):
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert isinstance(twd.root, TrackedDirectory)
        assert twd.root.path == tmp_path

    def test_discovers_child_with_claude_dir(self, tmp_path):
        (tmp_path / "subdir" / ".claude" / "sessions").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert len(twd.children) == 1
        assert twd.children[0].path == tmp_path / "subdir"
        assert twd.children[0].legacy is not None

    def test_discovers_child_with_hitl_dir(self, tmp_path):
        (tmp_path / "subdir" / ".hitl" / "sessions").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert len(twd.children) == 1
        assert twd.children[0].path == tmp_path / "subdir"
        assert twd.children[0].hitl is not None

    def test_discovers_multiple_children(self, tmp_path):
        (tmp_path / "app-a" / ".claude" / "sessions").mkdir(parents=True)
        (tmp_path / "app-b" / ".hitl" / "issues").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        child_paths = sorted(c.path.name for c in twd.children)
        assert child_paths == ["app-a", "app-b"]

    def test_no_children_when_no_subdirectory_tracking(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert twd.children == []

    def test_skips_git_and_node_modules(self, tmp_path):
        (tmp_path / ".git" / ".claude" / "sessions").mkdir(parents=True)
        (tmp_path / "node_modules" / ".claude" / "sessions").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert twd.children == []

    def test_does_not_include_root_as_child(self, tmp_path):
        (tmp_path / ".claude" / "sessions").mkdir(parents=True)
        (tmp_path / "subdir" / ".claude" / "sessions").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert len(twd.children) == 1
        assert twd.children[0].path == tmp_path / "subdir"

    def test_discovers_nested_child(self, tmp_path):
        (tmp_path / "a" / "b" / ".claude" / "sessions").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert len(twd.children) == 1
        assert twd.children[0].path == tmp_path / "a" / "b"

    def test_child_without_sessions_or_issues_not_included(self, tmp_path):
        (tmp_path / "subdir" / ".claude").mkdir(parents=True)
        twd = TrackedWorkingDirectory.scan(tmp_path)
        assert twd.children == []
