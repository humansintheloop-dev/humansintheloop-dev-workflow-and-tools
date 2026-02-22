"""Domain model for tracking directory structures."""

import os
import shutil
from pathlib import Path


class TrackingDir:
    """Wraps a path to a tracking subdirectory (sessions or issues)."""

    def __init__(self, path):
        self.path = Path(path)

    @property
    def exists(self):
        return self.path.exists()

    @property
    def is_symlink(self):
        return self.path.is_symlink()

    @property
    def symlink_target(self):
        if not self.path.is_symlink():
            return None
        return os.readlink(str(self.path))

    def list_files(self):
        if not self.path.exists():
            return []
        return sorted(entry.name for entry in self.path.iterdir() if entry.is_file())

    def migrate_to(self, target):
        if not self.path.exists():
            return
        for entry in self.path.iterdir():
            dst = target.path / entry.name
            if not dst.exists():
                shutil.move(str(entry), str(dst))


class LegacyTracking:
    """Legacy .claude tracking directory containing sessions and issues."""

    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.sessions = TrackingDir(self.base_path / "sessions")
        self.issues = TrackingDir(self.base_path / "issues")


class HitlTracking:
    """HITL .hitl tracking directory containing sessions and issues."""

    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.sessions = TrackingDir(self.base_path / "sessions")
        self.issues = TrackingDir(self.base_path / "issues")


class TrackedDirectory:
    """A directory that may contain legacy and/or HITL tracking."""

    def __init__(self, path, legacy, hitl):
        self.path = Path(path)
        self.legacy = legacy
        self.hitl = hitl

    @classmethod
    def from_path(cls, path):
        path = Path(path)
        legacy = cls._detect_legacy(path)
        hitl = cls._detect_hitl(path)
        return cls(path, legacy, hitl)

    @property
    def status(self):
        has_legacy = self.legacy is not None
        has_hitl = self.hitl is not None
        if has_legacy and has_hitl:
            return "both"
        if has_legacy:
            return "legacy"
        if has_hitl:
            return "hitl"
        return "none"

    @staticmethod
    def _detect_legacy(path):
        claude_dir = path / ".claude"
        if not claude_dir.is_dir():
            return None
        lt = LegacyTracking(claude_dir)
        if lt.sessions.exists or lt.issues.exists:
            return lt
        return None

    @staticmethod
    def _detect_hitl(path):
        hitl_dir = path / ".hitl"
        if not hitl_dir.is_dir():
            return None
        ht = HitlTracking(hitl_dir)
        if ht.sessions.exists or ht.issues.exists:
            return ht
        return None


SKIP_DIRS = {".git", "node_modules", ".hitl", ".claude"}


class TrackedWorkingDirectory:
    """A working directory tree with a root TrackedDirectory and discovered children."""

    def __init__(self, root, children):
        self.root = root
        self.children = children

    @classmethod
    def scan(cls, path):
        path = Path(path)
        root = TrackedDirectory.from_path(path)
        children = cls._discover_children(path)
        return cls(root, children)

    @classmethod
    def _discover_children(cls, root_path):
        children = []
        for dirpath, dirnames, _ in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            current = Path(dirpath)
            if current == root_path:
                continue
            td = TrackedDirectory.from_path(current)
            if td.status != "none":
                children.append(td)
        return children
