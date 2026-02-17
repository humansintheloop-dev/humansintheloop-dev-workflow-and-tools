"""FakeGitHubClient: test double for GitHubClient.

Separated into its own module so tests can import it unambiguously
regardless of pytest's conftest resolution order.
"""


class FakeGitHubClient:
    """Test double for GitHubClient that returns canned responses.

    Usage:
        fake = FakeGitHubClient()
        fake.set_pr_list([{"number": 42, "headRefName": "my-branch", "isDraft": True}])
        fake.set_pr_view(42, {"isDraft": True})
        fake.set_pr_url(42, "https://github.com/owner/repo/pull/42")
        fake.set_pr_state(42, "OPEN")

        result = fake.find_pr("my-branch")
        assert result == 42
    """

    def __init__(self):
        self._pr_list = []
        self._pr_views = {}
        self._pr_urls = {}
        self._pr_states = {}
        self._created_prs = []
        self._ready_prs = set()
        self._next_pr_number = 100
        self.calls = []

    def set_pr_list(self, prs):
        self._pr_list = prs

    def set_pr_view(self, pr_number, data):
        self._pr_views[pr_number] = data

    def set_pr_url(self, pr_number, url):
        self._pr_urls[pr_number] = url

    def set_pr_state(self, pr_number, state):
        self._pr_states[pr_number] = state

    def set_next_pr_number(self, number):
        self._next_pr_number = number

    def find_pr(self, branch_name):
        self.calls.append(("find_pr", branch_name))
        for pr in self._pr_list:
            if pr.get("headRefName") == branch_name:
                return pr.get("number")
        return None

    def create_draft_pr(self, slice_branch, title, body, base_branch):
        self.calls.append(("create_draft_pr", slice_branch, title, body, base_branch))
        pr_number = self._next_pr_number
        self._created_prs.append({
            "number": pr_number,
            "head": slice_branch,
            "title": title,
            "body": body,
            "base": base_branch,
        })
        self._next_pr_number += 1
        return pr_number

    def is_pr_draft(self, pr_number):
        self.calls.append(("is_pr_draft", pr_number))
        view = self._pr_views.get(pr_number, {})
        return view.get("isDraft", False)

    def get_pr_state(self, pr_number):
        self.calls.append(("get_pr_state", pr_number))
        return self._pr_states.get(pr_number, "")

    def get_pr_url(self, pr_number):
        self.calls.append(("get_pr_url", pr_number))
        return self._pr_urls.get(pr_number, "")

    def mark_pr_ready(self, pr_number):
        self.calls.append(("mark_pr_ready", pr_number))
        self._ready_prs.add(pr_number)
        return True
