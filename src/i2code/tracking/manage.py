"""Manage HITL tracking directories: migrate from .claude and create symlinks."""

import os
import shutil

import click

from i2code.tracking.model import TrackedWorkingDirectory, _symlink_already_correct


SUBDIRS = ("issues", "sessions")


def setup_tracking(project_dir, target_link=None, dry_run=False):
    """Set up HITL tracking: migrate from .claude/ and optionally link to shared directory."""
    twd = TrackedWorkingDirectory.scan(project_dir)
    migrate_tracking(twd, dry_run)
    if target_link:
        link_tracking(project_dir, target_link, dry_run)


def migrate_tracking(twd, dry_run=False):
    """Migrate root and children from legacy (.claude) to HITL (.hitl) tracking."""
    twd.migrate(dry_run)


def link_tracking(project_dir, target_base, dry_run=False):
    """Create symlinks from .hitl/issues and .hitl/sessions to target_base subdirectories."""
    _LinkExecutor(project_dir, dry_run).link(target_base)


class _LinkExecutor:
    """Executes symlink creation from .hitl to target directories."""

    def __init__(self, project_dir, dry_run=False):
        self.project_dir = project_dir
        self.dry_run = dry_run
        self.hitl_dir = os.path.join(project_dir, ".hitl")

    def link(self, target_base):
        """Create symlinks from .hitl/issues and .hitl/sessions to target_base."""
        self._check_for_conflicting_symlinks(target_base)
        print(f"Linking .hitl/{{issues,sessions}} -> {target_base}/...")

        for subdir in SUBDIRS:
            src = os.path.join(self.hitl_dir, subdir)
            target = os.path.join(target_base, subdir)

            self._ensure_directory(target)

            if _symlink_already_correct(src, target):
                print(f"  {self._rel(src)} already linked to {target}")
                continue

            self._clear_existing_path(src, target)
            self._create_symlink(src, target)

    def _check_for_conflicting_symlinks(self, target_base):
        for subdir in SUBDIRS:
            src = os.path.join(self.hitl_dir, subdir)
            target = os.path.join(target_base, subdir)
            if os.path.islink(src) and os.readlink(src) != target:
                existing_target = os.readlink(src)
                raise click.ClickException(
                    f".hitl/{subdir} is already linked to {existing_target} "
                    f"which is a different directory than {target}"
                )

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
