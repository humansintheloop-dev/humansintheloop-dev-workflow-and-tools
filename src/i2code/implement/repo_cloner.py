"""RepoCloner: creates a local clone of a repository for isolated work."""

import os
import subprocess


def clone_path_for(repo_root, idea_name):
    """Return the clone directory path for a given repo root and idea name.

    The clone is placed alongside the repo root directory:
        /path/to/repo -> /path/to/repo-cl-idea_name
    """
    parent_dir = os.path.dirname(repo_root)
    basename = os.path.basename(repo_root)
    return os.path.join(parent_dir, f"{basename}-cl-{idea_name}")


class RepoCloner:
    """Creates a local clone of a repository for isolated work."""

    def create_clone(self, source_path, idea_name, origin_url, clone_base=None):
        """Create a shallow clone of source_path for isolated work.

        If the clone directory already exists, returns its path without re-cloning.
        After cloning, reconfigures the clone's origin remote to point to origin_url
        (the GitHub remote) instead of the local source path.

        Args:
            source_path: The git repository to clone from.
            idea_name: The idea name used in the clone directory name.
            origin_url: The GitHub remote URL to set on the clone.
            clone_base: Path used to derive the clone directory name.
                Defaults to source_path when not provided.

        Returns:
            The path to the clone directory.
        """
        clone_dir = clone_path_for(clone_base or source_path, idea_name)
        if os.path.isdir(clone_dir):
            return clone_dir

        subprocess.run(
            ["git", "clone", "--depth", "1", source_path, clone_dir],
            check=True,
        )
        subprocess.run(
            ["git", "remote", "set-url", "origin", origin_url],
            cwd=clone_dir,
            check=True,
        )
        return clone_dir
