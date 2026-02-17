"""FakeGitRepository: test double for GitRepository.

Separated into its own module so tests can import it unambiguously
regardless of pytest's conftest resolution order.
"""


class FakeGitRepository:
    """Test double for GitRepository that returns canned responses.

    Usage:
        fake = FakeGitRepository(working_tree_dir="/fake/repo")
        fake.set_head_sha("abc123")
        assert fake.head_sha == "abc123"
    """

    def __init__(self, working_tree_dir="/fake/repo"):
        self._working_tree_dir = working_tree_dir
        self._head_sha = "aaa"
        self._branches = set()
        self._checked_out = None
        self._worktrees = {}
        self.calls = []

    @property
    def working_tree_dir(self):
        return self._working_tree_dir

    @property
    def head_sha(self):
        return self._head_sha

    def set_head_sha(self, sha):
        self._head_sha = sha

    def head_advanced_since(self, original_sha):
        self.calls.append(("head_advanced_since", original_sha))
        return self._head_sha != original_sha

    def ensure_branch(self, branch_name, from_ref=None, remote=False):
        self.calls.append(("ensure_branch", branch_name, from_ref, remote))
        self._branches.add(branch_name)
        return branch_name

    def checkout(self, branch_name):
        self.calls.append(("checkout", branch_name))
        self._checked_out = branch_name

    def ensure_worktree(self, idea_name, branch_name):
        self.calls.append(("ensure_worktree", idea_name, branch_name))
        worktree_path = self._worktrees.get(
            idea_name,
            f"{self._working_tree_dir}-wt-{idea_name}",
        )
        return worktree_path

    def set_worktree_path(self, idea_name, path):
        self._worktrees[idea_name] = path
