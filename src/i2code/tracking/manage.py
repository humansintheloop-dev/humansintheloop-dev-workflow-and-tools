"""Manage HITL tracking directories: migrate from .claude and create symlinks."""

import os
import shutil


SUBDIRS = ("issues", "sessions")


def migrate(project_dir, dry_run=False):
    """Move .claude/issues and .claude/sessions to .hitl/, update .gitignore."""
    claude_dir = os.path.join(project_dir, ".claude")
    hitl_dir = os.path.join(project_dir, ".hitl")

    moved_any = False
    for subdir in SUBDIRS:
        src = os.path.join(claude_dir, subdir)
        dst = os.path.join(hitl_dir, subdir)

        if not os.path.exists(src):
            continue

        if os.path.islink(src):
            _migrate_symlink(project_dir, src, dst, dry_run)
            moved_any = True
            continue

        if os.path.exists(dst):
            _merge_into_existing(project_dir, src, dst, dry_run)
            moved_any = True
            continue

        print(f"  Move {_rel(project_dir, src)} -> {_rel(project_dir, dst)}")
        if not dry_run:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
        moved_any = True

    _update_gitignore(project_dir, dry_run)

    if not moved_any:
        print("  Nothing to migrate")

    _warn_stale_subdirectories(project_dir)


def _migrate_symlink(project_dir, src, dst, dry_run):
    """Migrate a .claude/<subdir> symlink to .hitl/<subdir>.

    If .hitl/<subdir> is a real directory, move its contents into the
    symlink target first, then replace the directory with a symlink.
    """
    link_target = os.readlink(src)

    dst_cleared = False
    if os.path.isdir(dst) and not os.path.islink(dst):
        # Remove debug.log before moving — it will be recreated
        debug_log = os.path.join(dst, "debug.log")
        if os.path.isfile(debug_log):
            print(f"  Remove {_rel(project_dir, debug_log)}")
            if not dry_run:
                os.remove(debug_log)
        # Move remaining contents to the symlink target
        entries = [e for e in os.listdir(dst) if e != "debug.log"]
        if entries:
            print(f"  Move {len(entries)} file(s) from {_rel(project_dir, dst)} to {link_target}")
            if not dry_run:
                for entry in entries:
                    entry_src = os.path.join(dst, entry)
                    entry_dst = os.path.join(link_target, entry)
                    if not os.path.exists(entry_dst):
                        shutil.move(entry_src, entry_dst)
        print(f"  Remove empty directory {_rel(project_dir, dst)}")
        if not dry_run:
            os.rmdir(dst)
        dst_cleared = True

    if os.path.islink(dst) and os.readlink(dst) == link_target:
        print(f"  {_rel(project_dir, dst)} already linked to {link_target}")
    elif not dst_cleared and (os.path.exists(dst) or os.path.islink(dst)):
        print(f"  Skipping {_rel(project_dir, src)} (destination {_rel(project_dir, dst)} already exists)")
        return
    else:
        if not dry_run:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
        print(f"  Symlink {_rel(project_dir, dst)} -> {link_target}")
        if not dry_run:
            os.symlink(link_target, dst)

    print(f"  Remove {_rel(project_dir, src)}")
    if not dry_run:
        os.remove(src)


def _merge_into_existing(project_dir, src, dst, dry_run):
    """Merge files from src into dst, then remove src.

    Walks src recursively, moving files that don't exist in dst.
    Ignores debug.log.
    """
    moved = 0
    for dirpath, _, filenames in os.walk(src):
        rel_dir = os.path.relpath(dirpath, src)
        dst_dir = os.path.join(dst, rel_dir) if rel_dir != "." else dst

        for fname in filenames:
            if fname == "debug.log":
                continue
            file_src = os.path.join(dirpath, fname)
            file_dst = os.path.join(dst_dir, fname)
            if os.path.exists(file_dst):
                continue
            if not dry_run:
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(file_src, file_dst)
            moved += 1

    if moved:
        print(f"  Move {moved} file(s) from {_rel(project_dir, src)} to {_rel(project_dir, dst)}")

    print(f"  Remove {_rel(project_dir, src)}")
    if not dry_run:
        shutil.rmtree(src)


def link(project_dir, target_base, dry_run=False):
    """Create symlinks from .hitl/issues and .hitl/sessions to target_base subdirectories."""
    hitl_dir = os.path.join(project_dir, ".hitl")

    for subdir in SUBDIRS:
        src = os.path.join(hitl_dir, subdir)
        target = os.path.join(target_base, subdir)

        # Create target directory
        if not os.path.isdir(target):
            print(f"  Create directory {target}")
            if not dry_run:
                os.makedirs(target, exist_ok=True)

        # Handle existing source path
        if os.path.exists(src) or os.path.islink(src):
            if os.path.islink(src):
                current = os.readlink(src)
                if current == target:
                    print(f"  {_rel(project_dir, src)} already linked to {target}")
                    continue
                print(f"  Remove old symlink {_rel(project_dir, src)} -> {current}")
                if not dry_run:
                    os.remove(src)
            else:
                # Move contents to target, then remove directory
                entries = os.listdir(src)
                if entries:
                    print(f"  Move {len(entries)} file(s) from {_rel(project_dir, src)} to {target}")
                    if not dry_run:
                        for entry in entries:
                            entry_src = os.path.join(src, entry)
                            entry_dst = os.path.join(target, entry)
                            if not os.path.exists(entry_dst):
                                shutil.move(entry_src, entry_dst)
                print(f"  Remove directory {_rel(project_dir, src)}")
                if not dry_run:
                    shutil.rmtree(src)

        # Ensure parent exists
        if not dry_run:
            os.makedirs(os.path.dirname(src), exist_ok=True)

        print(f"  Symlink {_rel(project_dir, src)} -> {target}")
        if not dry_run:
            os.symlink(target, src)


def _update_gitignore(project_dir, dry_run):
    """Replace .claude/issues and .claude/sessions entries with .hitl in .gitignore."""
    gitignore = os.path.join(project_dir, ".gitignore")
    if not os.path.isfile(gitignore):
        return

    with open(gitignore, "r") as f:
        lines = f.readlines()

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

    if not removed and has_hitl:
        print("  .gitignore already up to date")
        return

    if removed:
        for r in removed:
            print(f"  Remove .gitignore entry: {r}")

    if not has_hitl:
        insert_pos = _find_gitignore_insert_position(new_lines)
        new_lines.insert(insert_pos, "**/.hitl\n")
        print("  Add .gitignore entry: **/.hitl")

    if not dry_run:
        with open(gitignore, "w") as f:
            f.writelines(new_lines)


def _find_gitignore_insert_position(lines):
    """Find a reasonable position to insert the .hitl entry."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return i
    return len(lines)


def _warn_stale_subdirectories(project_dir):
    """Warn about .claude/issues or .claude/sessions dirs in subdirectories.

    These were previously gitignored by **/.claude/sessions etc. but are
    no longer ignored after switching to **/.hitl.
    """
    stale = []
    for dirpath, dirnames, _ in os.walk(project_dir):
        # Don't descend into .git or node_modules
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]

        if os.path.basename(dirpath) == ".claude" and dirpath != os.path.join(project_dir, ".claude"):
            for subdir in SUBDIRS:
                candidate = os.path.join(dirpath, subdir)
                if os.path.exists(candidate):
                    stale.append(_rel(project_dir, candidate))

    if stale:
        print("\n  Warning: the following subdirectories are no longer gitignored")
        print("  (previously covered by **/.claude/sessions and **/.claude/issues):\n")
        for path in sorted(stale):
            print(f"    {path}")


def _rel(base, path):
    """Return path relative to base for display."""
    return os.path.relpath(path, base)
