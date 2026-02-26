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

    def __init__(self, working_tree_dir="/fake/repo", gh_client=None, main_repo_dir=None):
        self._working_tree_dir = working_tree_dir
        self._gh_client = gh_client
        self._main_repo_dir = main_repo_dir or working_tree_dir
        self._origin_url = "https://github.com/test/repo.git"
        self._user_config = ("Test", "test@test.com")
        self._head_sha = "aaa"
        self._branches = set()
        self._checked_out = None
        self._worktrees = {}
        self._clone_repos = {}
        self._pushed = False
        self._default_diff_output = ""
        self._diff_outputs = {}
        self._files_at_head = {}
        self.branch = None
        self.pr_number = None
        self.calls = []

    @property
    def main_repo_dir(self):
        return self._main_repo_dir

    @property
    def gh_client(self):
        return self._gh_client

    @property
    def working_tree_dir(self):
        return self._working_tree_dir

    @property
    def is_worktree(self):
        return self._working_tree_dir != self._main_repo_dir

    @property
    def origin_url(self):
        return self._origin_url

    def set_origin_url(self, url):
        self._origin_url = url

    @property
    def head_sha(self):
        return self._head_sha

    def set_head_sha(self, sha):
        self._head_sha = sha

    def add_and_commit(self, file_path, message):
        self.calls.append(("add_and_commit", file_path, message))

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
        return FakeGitRepository(
            working_tree_dir=worktree_path,
            main_repo_dir=self._working_tree_dir,
        )

    def set_worktree_path(self, idea_name, path):
        self._worktrees[idea_name] = path

    def set_clone_repo(self, idea_name, git_repo):
        self._clone_repos[idea_name] = git_repo

    def find_clone(self, idea_name):
        self.calls.append(("find_clone", idea_name))
        return self._clone_repos.get(idea_name)

    def clone(self, idea_name):
        self.calls.append(("clone", idea_name))
        clone_path = f"{self._working_tree_dir}-cl-{idea_name}"
        return FakeGitRepository(
            working_tree_dir=clone_path,
            main_repo_dir=self._main_repo_dir,
        )

    def has_unpushed_commits(self):
        self.calls.append(("has_unpushed_commits",))
        return not self._pushed

    def set_upstream(self, branch_name):
        self.calls.append(("set_upstream", branch_name))

    def branch_has_been_pushed(self):
        self.calls.append(("branch_has_been_pushed",))
        return self._pushed

    def set_pushed(self, pushed):
        self._pushed = pushed

    def push(self):
        self.calls.append(("push",))
        self._pushed = True
        return True

    def get_user_config(self):
        self.calls.append(("get_user_config",))
        return self._user_config

    def set_user_config(self, name, email):
        self.calls.append(("set_user_config", name, email))

    def diff_file_against_head(self, file_path):
        self.calls.append(("diff_file_against_head", file_path))
        if file_path in self._diff_outputs:
            return self._diff_outputs[file_path]
        return self._default_diff_output

    def set_diff_output(self, diff_output, file_path=None):
        if file_path is None:
            self._default_diff_output = diff_output
        else:
            self._diff_outputs[file_path] = diff_output

    def show_file_at_head(self, file_path):
        self.calls.append(("show_file_at_head", file_path))
        return self._files_at_head.get(file_path, "")

    def set_file_at_head(self, file_path, content):
        self._files_at_head[file_path] = content

    def ensure_idea_branch(self, idea_name):
        branch_name = f"idea/{idea_name}"
        return self.ensure_branch(branch_name)

    def ensure_pr(self, idea_directory, idea_name):
        self.calls.append(("ensure_pr", idea_directory, idea_name))
        if self.pr_number is None:
            self.pr_number = 100
        return self.pr_number

