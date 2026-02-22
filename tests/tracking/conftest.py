"""Shared fixtures and helpers for directory-based tracking test cases."""

import os
import shutil
from pathlib import Path

SENTINEL = ".keep"


def create_tree(tmp_path, before_dir):
    """Copy before/ contents into tmp_path, converting .symlink markers to real symlinks.

    - ``dotclaude`` directories are renamed to ``.claude`` in the copy.
    - ``.symlink`` file content may use ``$ROOT`` as a placeholder for tmp_path.
    """
    before = Path(before_dir)
    for src in sorted(before.rglob("*")):
        rel = _rename_dot_dirs(src.relative_to(before))
        dst = tmp_path / rel
        if src.is_dir() and not src.name.endswith(".symlink"):
            dst.mkdir(parents=True, exist_ok=True)
        elif src.name.endswith(".symlink"):
            target = _expand_root(src.read_text().strip(), tmp_path)
            dst = tmp_path / rel.parent / rel.stem
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(target, str(dst))
        elif src.is_file() and src.name != SENTINEL:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))


def assert_tree(tmp_path, before_dir, after_dir):
    """Assert tmp_path matches after/, and paths in before/ but not after/ are absent."""
    before = Path(before_dir)
    after = Path(after_dir)
    _assert_expected_paths(tmp_path, after)
    _assert_removed_paths(tmp_path, before, after)


def _assert_expected_paths(tmp_path, after):
    for src in sorted(after.rglob("*")):
        if src.name == SENTINEL:
            continue
        rel = _rename_dot_dirs(src.relative_to(after))
        if src.name.endswith(".symlink"):
            _assert_symlink(tmp_path, rel, src)
        elif src.is_file():
            _assert_file(tmp_path, rel, src)
        elif src.is_dir():
            assert (tmp_path / rel).is_dir(), f"Expected directory at {rel}"


def _assert_symlink(tmp_path, rel, src):
    expected_target = _expand_root(src.read_text().strip(), tmp_path)
    real_path = tmp_path / rel.parent / rel.stem
    assert real_path.is_symlink(), f"Expected symlink at {rel.parent / rel.stem}"
    assert os.readlink(str(real_path)) == expected_target, (
        f"Symlink {rel.parent / rel.stem} points to {os.readlink(str(real_path))}, "
        f"expected {expected_target}"
    )


def _assert_file(tmp_path, rel, src):
    dst = tmp_path / rel
    assert dst.is_file(), f"Expected file at {rel}"
    assert dst.read_text() == src.read_text(), f"Content mismatch at {rel}"


def _assert_removed_paths(tmp_path, before, after):
    before_rels = _collect_rels(before)
    after_rels = _collect_rels(after)
    after_symlinks = _collect_symlink_dirs(after)
    for rel in before_rels - after_rels:
        if _under_symlink(rel, after_symlinks):
            continue
        absent = tmp_path / rel
        assert not absent.exists() and not absent.is_symlink(), (
            f"Expected {rel} to be absent"
        )


DOT_RENAMES = {"dotclaude": ".claude", "dothitl": ".hitl"}


def _rename_dot_dirs(rel):
    """Rename ``dotclaude`` and ``dothitl`` path components to ``.claude`` and ``.hitl``."""
    parts = [DOT_RENAMES.get(p, p) for p in rel.parts]
    return Path(*parts) if parts else rel


def _expand_root(target, tmp_path):
    """Replace $ROOT placeholder with actual tmp_path."""
    return target.replace("$ROOT", str(tmp_path))


def _collect_rels(tree_dir):
    """Collect relative paths from a tree, normalizing .symlink and dotclaude."""
    rels = set()
    for p in tree_dir.rglob("*"):
        if p.name == SENTINEL:
            continue
        rel = _rename_dot_dirs(p.relative_to(tree_dir))
        if p.name.endswith(".symlink"):
            rels.add(rel.parent / rel.stem)
        else:
            rels.add(rel)
    return rels


def _collect_symlink_dirs(tree_dir):
    """Collect directory-level relative paths that are .symlink markers."""
    dirs = set()
    for p in tree_dir.rglob("*.symlink"):
        rel = _rename_dot_dirs(p.relative_to(tree_dir))
        dirs.add(rel.parent / rel.stem)
    return dirs


def _under_symlink(rel, symlink_dirs):
    """Check if rel is a descendant of any symlink directory."""
    for sym in symlink_dirs:
        try:
            rel.relative_to(sym)
            return True
        except ValueError:
            continue
    return False
