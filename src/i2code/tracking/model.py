"""Domain model for tracking directory structures."""

import os
import shutil
from pathlib import Path


_rel = os.path.relpath


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

    def link_to_root(self, root, dry_run):
        """Create symlink to root if root tracks this subdir."""
        dst = os.path.join(root.hitl_path, self.path.name)
        if not os.path.isdir(dst):
            return
        _ensure_symlink(str(self.path), dst, dry_run)

    def consolidate_into_root(self, root, dry_run):
        """Merge real directory contents into root and create symlink back."""
        if not self.path.is_dir() or self.is_symlink:
            return
        dst = os.path.join(root.hitl_path, self.path.name)
        if not dry_run:
            os.makedirs(dst, exist_ok=True)
        _merge_into_existing(str(self.path), dst, dry_run)
        self.link_to_root(root, dry_run)


class LegacyTracking:
    """Legacy .claude tracking directory containing sessions and issues."""

    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.sessions = TrackingDir(self.base_path / "sessions")
        self.issues = TrackingDir(self.base_path / "issues")

    def consolidate_into(self, root, dry_run):
        """Move real directory contents to root and remove source."""
        for td in (self.sessions, self.issues):
            if td.is_symlink:
                self._remove_legacy_symlink(td, dry_run)
                continue
            if not td.exists:
                continue
            dst = os.path.join(root.hitl_path, td.path.name)
            if not dry_run:
                os.makedirs(dst, exist_ok=True)
            _merge_into_existing(str(td.path), dst, dry_run)

    @staticmethod
    def _remove_legacy_symlink(td, dry_run):
        print(f"  Remove legacy symlink {_rel(str(td.path))}")
        if not dry_run:
            os.remove(str(td.path))


class HitlTracking:
    """HITL .hitl tracking directory containing sessions and issues."""

    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.sessions = TrackingDir(self.base_path / "sessions")
        self.issues = TrackingDir(self.base_path / "issues")

    def consolidate_into(self, root, dry_run):
        """Move real directory contents to root and replace with symlinks."""
        for td in (self.sessions, self.issues):
            td.consolidate_into_root(root, dry_run)

    def link_to_root(self, root, dry_run):
        """Create symlinks to root for each subdir that root tracks."""
        for td in (self.sessions, self.issues):
            td.link_to_root(root, dry_run)


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
    def hitl_path(self):
        return str(self.path / ".hitl")

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

    def consolidate_into(self, root, dry_run=False):
        """Consolidate this child's tracking into root .hitl/."""
        if self.legacy is not None:
            self.legacy.consolidate_into(root, dry_run)
        if self.hitl is not None:
            self.hitl.consolidate_into(root, dry_run)
        if self.legacy is not None and self.hitl is None:
            hitl = HitlTracking(Path(self.hitl_path))
            hitl.link_to_root(root, dry_run)
            if not dry_run:
                self.hitl = hitl

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

    def migrate(self, dry_run=False):
        """Migrate root tracking and consolidate children."""
        self._migrate_root(dry_run)
        self._consolidate_children(dry_run)

    def _migrate_root(self, dry_run):
        self._update_gitignore(dry_run)
        self._ensure_hitl_dirs(dry_run)
        if self.root.legacy is None:
            return

        print("Migrating .claude/{issues,sessions} -> .hitl/...")
        for td in (self.root.legacy.sessions, self.root.legacy.issues):
            if not td.exists:
                continue
            dst = os.path.join(self.root.hitl_path, td.path.name)
            self._migrate_root_subdir(td, dst, dry_run)

    def _ensure_hitl_dirs(self, dry_run):
        for subdir in ("sessions", "issues"):
            path = os.path.join(self.root.hitl_path, subdir)
            if not os.path.isdir(path):
                if not dry_run:
                    os.makedirs(path, exist_ok=True)

    def _migrate_root_subdir(self, tracking_dir, dst, dry_run):
        src = str(tracking_dir.path)
        if tracking_dir.is_symlink:
            self._migrate_symlink(src, dst, dry_run)
        elif os.path.exists(dst):
            _merge_into_existing(src, dst, dry_run)
        else:
            _move_directory(src, dst, dry_run)

    def _migrate_symlink(self, src, dst, dry_run):
        link_target = os.readlink(src)
        dst_cleared = _absorb_real_dir_into_target(dst, link_target, dry_run)

        if _symlink_already_correct(dst, link_target):
            print(f"  {_rel(dst)} already linked to {link_target}")
        elif _destination_blocked(dst, dst_cleared):
            print(
                f"  Skipping {_rel(src)} "
                f"(destination {_rel(dst)} already exists)"
            )
            return
        else:
            _create_symlink(dst, link_target, dry_run)

        _remove_path(src, dry_run)

    def _update_gitignore(self, dry_run):
        gitignore = os.path.join(str(self.root.path), ".gitignore")
        if not os.path.isfile(gitignore):
            print("  Add .gitignore entry: **/.hitl")
            if not dry_run:
                with open(gitignore, "w") as f:
                    f.write("**/.hitl\n")
            return

        with open(gitignore, "r") as f:
            lines = f.readlines()

        new_lines, removed, has_hitl = _filter_gitignore_entries(lines)

        if not removed and has_hitl:
            return

        for r in removed:
            print(f"  Remove .gitignore entry: {r}")

        if not has_hitl:
            insert_pos = _find_gitignore_insert_position(new_lines)
            new_lines.insert(insert_pos, "**/.hitl\n")
            print("  Add .gitignore entry: **/.hitl")

        if not dry_run:
            with open(gitignore, "w") as f:
                f.writelines(new_lines)

    def _consolidate_children(self, dry_run):
        for child in self.children:
            child.consolidate_into(self.root, dry_run)

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


# -- filesystem helpers --


def _merge_into_existing(src, dst, dry_run):
    moved = _move_tree_contents(src, dst, dry_run)
    if moved:
        print(f"  Move {moved} file(s) from {_rel(src)} to {_rel(dst)}")
    print(f"  Remove {_rel(src)}")
    if not dry_run:
        shutil.rmtree(src)


def _move_tree_contents(src, dst, dry_run):
    moved = 0
    for dirpath, _, filenames in os.walk(src):
        rel_dir = os.path.relpath(dirpath, src)
        dst_dir = os.path.join(dst, rel_dir) if rel_dir != "." else dst
        moved += _move_new_files(dirpath, dst_dir, filenames, dry_run)
    return moved


def _move_new_files(src_dir, dst_dir, filenames, dry_run):
    moved = 0
    for file_src, file_dst in _new_file_pairs(src_dir, dst_dir, filenames):
        if not dry_run:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(file_src, file_dst)
        moved += 1
    return moved


def _move_directory(src, dst, dry_run):
    print(f"  Move {_rel(src)} -> {_rel(dst)}")
    if not dry_run:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)


def _create_symlink(path, target, dry_run):
    if not dry_run:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"  Symlink {_rel(path)} -> {target}")
    if not dry_run:
        os.symlink(target, path)


def _remove_path(path, dry_run):
    print(f"  Remove {_rel(path)}")
    if not dry_run:
        os.remove(path)


def _ensure_symlink(link_path, target, dry_run):
    rel_target = os.path.relpath(target, os.path.dirname(link_path))
    if _symlink_already_correct(link_path, rel_target):
        print(f"  {_rel(link_path)} already linked to {rel_target}")
        return
    print(f"  Symlink {_rel(link_path)} -> {rel_target}")
    if not dry_run:
        os.makedirs(os.path.dirname(link_path), exist_ok=True)
        os.symlink(rel_target, link_path)


def _absorb_real_dir_into_target(dst, link_target, dry_run):
    if not os.path.isdir(dst) or os.path.islink(dst):
        return False
    _remove_debug_log(dst, dry_run)
    _move_filtered_entries(dst, link_target, dry_run)
    print(f"  Remove empty directory {_rel(dst)}")
    if not dry_run:
        os.rmdir(dst)
    return True


def _remove_debug_log(directory, dry_run):
    debug_log = os.path.join(directory, "debug.log")
    if not os.path.isfile(debug_log):
        return
    print(f"  Remove {_rel(debug_log)}")
    if not dry_run:
        os.remove(debug_log)


def _move_filtered_entries(src_dir, target_dir, dry_run):
    entries = [e for e in os.listdir(src_dir) if e != "debug.log"]
    if not entries:
        return
    print(
        f"  Move {len(entries)} file(s) from {_rel(src_dir)} to {target_dir}"
    )
    if not dry_run:
        for entry in entries:
            entry_dst = os.path.join(target_dir, entry)
            if not os.path.exists(entry_dst):
                shutil.move(os.path.join(src_dir, entry), entry_dst)


# -- pure functions --


def _symlink_already_correct(path, expected_target):
    return os.path.islink(path) and os.readlink(path) == expected_target


def _destination_blocked(dst, dst_cleared):
    return not dst_cleared and (os.path.exists(dst) or os.path.islink(dst))


def _new_file_pairs(src_dir, dst_dir, filenames):
    for fname in filenames:
        if fname == "debug.log":
            continue
        file_dst = os.path.join(dst_dir, fname)
        if not os.path.exists(file_dst):
            yield os.path.join(src_dir, fname), file_dst


def _filter_gitignore_entries(lines):
    old_patterns = {
        ".claude/issues", ".claude/sessions",
        "**/.claude/issues", "**/.claude/sessions",
    }
    new_lines = []
    removed = []
    has_hitl = False

    for line in lines:
        stripped = line.strip()
        if stripped in old_patterns:
            removed.append(stripped)
            continue
        if stripped in (".hitl", "**/.hitl"):
            has_hitl = True
        new_lines.append(line)

    return new_lines, removed, has_hitl


def _find_gitignore_insert_position(lines):
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return i
    return len(lines)
