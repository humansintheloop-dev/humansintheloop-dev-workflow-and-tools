"""FakeRepoCloner: test double for RepoCloner.

Records create_clone() calls and returns a configurable clone path.
"""


class FakeRepoCloner:
    """Test double for RepoCloner that records calls and returns a configurable clone path."""

    def __init__(self, clone_path="/fake/clone"):
        self._clone_path = clone_path
        self.calls = []

    def set_clone_path(self, path):
        self._clone_path = path

    def create_clone(self, source_path, idea_name, origin_url, clone_base=None):
        self.calls.append(("create_clone", source_path, idea_name, origin_url, clone_base))
        return self._clone_path
