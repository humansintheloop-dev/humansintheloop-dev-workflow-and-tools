"""Manage HITL tracking directories: migrate from .claude and create symlinks."""

import os
import shutil

from i2code.tracking.model import TrackedWorkingDirectory


SUBDIRS = ("issues", "sessions")


def migrate(project_dir, dry_run=False):
    """Move .claude/issues and .claude/sessions to .hitl/, update .gitignore."""
    twd = TrackedWorkingDirectory.scan(project_dir)
    migrate_tracking(twd, dry_run)


def link(project_dir, target_base, dry_run=False):
    """Create symlinks from .hitl/issues and .hitl/sessions to target_base subdirectories."""
    _LinkExecutor(project_dir, dry_run).link(target_base)


def migrate_tracking(twd, dry_run=False):
    """Migrate root and children from legacy (.claude) to HITL (.hitl) tracking."""
    executor = _MigrateExecutor(str(twd.root.path), dry_run)
    executor.migrate_root()
    executor.migrate_children(twd.children)


def link_tracking(project_dir, target_base, dry_run=False):
    """Create symlinks from .hitl/issues and .hitl/sessions to target_base subdirectories."""
    _LinkExecutor(project_dir, dry_run).link(target_base)


class _MigrateExecutor:
    """Executes migration from .claude to .hitl tracking directories."""

    def __init__(self, project_dir, dry_run=False):
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.claude_dir = os.path.join(project_dir, ".claude")
        self.hitl_dir = os.path.join(project_dir, ".hitl")

    def migrate_root(self):
        """Move .claude/issues and .claude/sessions to .hitl/, update .gitignore."""
        moved_any = False
        for subdir in SUBDIRS:
            src = os.path.join(self.claude_dir, subdir)
            dst = os.path.join(self.hitl_dir, subdir)

            if not os.path.exists(src):
                continue

            if os.path.islink(src):
                self._migrate_symlink(src, dst)
            elif os.path.exists(dst):
                self._merge_into_existing(src, dst)
            else:
                self._move_directory(src, dst)
            moved_any = True

        self._update_gitignore()

        if not moved_any:
            print("  Nothing to migrate")

    def migrate_children(self, children):
        """Migrate tracking from child directories into root .hitl/."""
        for child in children:
            link_base = os.path.join(str(child.path), ".hitl")
            self._migrate_child_legacy(child, link_base)
            self._consolidate_child_hitl(child, link_base)

    def _migrate_child_legacy(self, child, link_base):
        """Consolidate a child's legacy (.claude) tracking into root and relink."""
        if child.legacy is None:
            return
        src_base = str(child.legacy.base_path)
        for subdir in SUBDIRS:
            self._consolidate_child_subdir(src_base, link_base, subdir)
            self._relink_legacy_symlink(src_base, link_base, subdir)

    def _consolidate_child_hitl(self, child, link_base):
        """Consolidate a child's .hitl tracking into root."""
        if child.hitl is None:
            return
        src_base = str(child.hitl.base_path)
        for subdir in SUBDIRS:
            self._consolidate_child_subdir(src_base, link_base, subdir)

    # -- migrate helpers --

    def _relink_legacy_symlink(self, src_base, link_base, subdir):
        """When a child's legacy subdir is a symlink, create .hitl symlink to root instead."""
        src = os.path.join(src_base, subdir)
        if not os.path.islink(src):
            return

        dst = os.path.join(self.hitl_dir, subdir)
        link_path = os.path.join(link_base, subdir)
        rel_target = os.path.relpath(dst, link_base)
        self._ensure_symlink(link_path, rel_target)

    def _consolidate_child_subdir(self, src_base, link_base, subdir):
        """Merge a child's tracking subdir into root .hitl/ and create symlink back."""
        src = os.path.join(src_base, subdir)
        if not os.path.isdir(src) or os.path.islink(src):
            return

        dst = os.path.join(self.hitl_dir, subdir)
        if not self.dry_run:
            os.makedirs(dst, exist_ok=True)
        self._merge_into_existing(src, dst)

        link_path = os.path.join(link_base, subdir)
        rel_target = os.path.relpath(dst, link_base)
        self._ensure_symlink(link_path, rel_target)

    def _migrate_symlink(self, src, dst):
        link_target = os.readlink(src)
        dst_cleared = self._absorb_real_dir_into_target(dst, link_target)

        if _symlink_already_correct(dst, link_target):
            print(f"  {self._rel(dst)} already linked to {link_target}")
        elif _destination_blocked(dst, dst_cleared):
            print(f"  Skipping {self._rel(src)} "
                  f"(destination {self._rel(dst)} already exists)")
            return
        else:
            self._create_symlink(dst, link_target)

        self._remove_path(src)

    def _absorb_real_dir_into_target(self, dst, link_target):
        if not os.path.isdir(dst) or os.path.islink(dst):
            return False

        self._remove_debug_log(dst)
        self._move_filtered_entries(dst, link_target)

        print(f"  Remove empty directory {self._rel(dst)}")
        if not self.dry_run:
            os.rmdir(dst)
        return True

    def _remove_debug_log(self, directory):
        debug_log = os.path.join(directory, "debug.log")
        if not os.path.isfile(debug_log):
            return
        print(f"  Remove {self._rel(debug_log)}")
        if not self.dry_run:
            os.remove(debug_log)

    def _move_directory(self, src, dst):
        print(f"  Move {self._rel(src)} -> {self._rel(dst)}")
        if not self.dry_run:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)

    def _merge_into_existing(self, src, dst):
        moved = self._move_tree_contents(src, dst)
        if moved:
            print(f"  Move {moved} file(s) from {self._rel(src)} "
                  f"to {self._rel(dst)}")
        print(f"  Remove {self._rel(src)}")
        if not self.dry_run:
            shutil.rmtree(src)

    def _move_tree_contents(self, src, dst):
        moved = 0
        for dirpath, _, filenames in os.walk(src):
            rel_dir = os.path.relpath(dirpath, src)
            dst_dir = os.path.join(dst, rel_dir) if rel_dir != "." else dst
            moved += self._move_new_files(dirpath, dst_dir, filenames)
        return moved

    def _move_new_files(self, src_dir, dst_dir, filenames):
        moved = 0
        for file_src, file_dst in _new_file_pairs(src_dir, dst_dir, filenames):
            if not self.dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(file_src, file_dst)
            moved += 1
        return moved

    def _update_gitignore(self):
        gitignore = os.path.join(self.project_dir, ".gitignore")
        if not os.path.isfile(gitignore):
            return

        with open(gitignore, "r") as f:
            lines = f.readlines()

        new_lines, removed, has_hitl = _filter_gitignore_entries(lines)

        if not removed and has_hitl:
            print("  .gitignore already up to date")
            return

        for r in removed:
            print(f"  Remove .gitignore entry: {r}")

        if not has_hitl:
            insert_pos = _find_gitignore_insert_position(new_lines)
            new_lines.insert(insert_pos, "**/.hitl\n")
            print("  Add .gitignore entry: **/.hitl")

        if not self.dry_run:
            with open(gitignore, "w") as f:
                f.writelines(new_lines)

    # -- shared helpers --

    def _create_symlink(self, path, target):
        if not self.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"  Symlink {self._rel(path)} -> {target}")
        if not self.dry_run:
            os.symlink(target, path)

    def _remove_path(self, path):
        print(f"  Remove {self._rel(path)}")
        if not self.dry_run:
            os.remove(path)

    def _ensure_symlink(self, link_path, rel_target):
        if _symlink_already_correct(link_path, rel_target):
            print(f"  {self._rel(link_path)} already linked to {rel_target}")
            return
        print(f"  Symlink {self._rel(link_path)} -> {rel_target}")
        if not self.dry_run:
            os.makedirs(os.path.dirname(link_path), exist_ok=True)
            os.symlink(rel_target, link_path)

    def _move_filtered_entries(self, src_dir, target_dir):
        entries = [e for e in os.listdir(src_dir) if e != "debug.log"]
        if not entries:
            return
        print(f"  Move {len(entries)} file(s) from {self._rel(src_dir)} "
              f"to {target_dir}")
        if not self.dry_run:
            for entry in entries:
                entry_dst = os.path.join(target_dir, entry)
                if not os.path.exists(entry_dst):
                    shutil.move(os.path.join(src_dir, entry), entry_dst)

    def _rel(self, path):
        return os.path.relpath(path, self.project_dir)


class _LinkExecutor:
    """Executes symlink creation from .hitl to target directories."""

    def __init__(self, project_dir, dry_run=False):
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.hitl_dir = os.path.join(project_dir, ".hitl")

    def link(self, target_base):
        """Create symlinks from .hitl/issues and .hitl/sessions to target_base."""
        for subdir in SUBDIRS:
            src = os.path.join(self.hitl_dir, subdir)
            target = os.path.join(target_base, subdir)

            self._ensure_directory(target)

            if _symlink_already_correct(src, target):
                print(f"  {self._rel(src)} already linked to {target}")
                continue

            self._clear_existing_path(src, target)
            self._create_symlink(src, target)

    def _clear_existing_path(self, src, target):
        if not os.path.exists(src) and not os.path.islink(src):
            return

        if os.path.islink(src):
            self._remove_old_symlink(src)
        else:
            self._replace_directory(src, target)

    def _remove_old_symlink(self, src):
        print(f"  Remove old symlink {self._rel(src)} -> {os.readlink(src)}")
        if not self.dry_run:
            os.remove(src)

    def _replace_directory(self, src, target):
        self._move_all_entries(src, target)
        print(f"  Remove directory {self._rel(src)}")
        if not self.dry_run:
            shutil.rmtree(src)

    def _move_all_entries(self, src_dir, target_dir):
        entries = os.listdir(src_dir)
        if not entries:
            return
        print(f"  Move {len(entries)} file(s) from {self._rel(src_dir)} "
              f"to {target_dir}")
        if not self.dry_run:
            for entry in entries:
                entry_dst = os.path.join(target_dir, entry)
                if not os.path.exists(entry_dst):
                    shutil.move(os.path.join(src_dir, entry), entry_dst)

    def _create_symlink(self, path, target):
        if not self.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        print(f"  Symlink {self._rel(path)} -> {target}")
        if not self.dry_run:
            os.symlink(target, path)

    def _ensure_directory(self, path):
        if os.path.isdir(path):
            return
        print(f"  Create directory {path}")
        if not self.dry_run:
            os.makedirs(path, exist_ok=True)

    def _rel(self, path):
        return os.path.relpath(path, self.project_dir)


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
    old_patterns = {".claude/issues", ".claude/sessions",
                    "**/.claude/issues", "**/.claude/sessions"}
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
