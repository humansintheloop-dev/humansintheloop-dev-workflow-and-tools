"""RepoCloner: creates a local clone of a repository for isolated work."""

import os


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

    def create_clone(self, source_path, idea_name, origin_url):
        raise NotImplementedError
