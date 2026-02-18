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
        self._pr_comments = {}
        self._pr_reviews = {}
        self._pr_conversation_comments = {}
        self._failed_checks = {}
        self._workflow_runs = {}
        self._workflow_failure_logs = {}
        self._default_branch = "main"
        self._reply_results = True
        self._workflow_completion_results = {}
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

    def set_pr_comments(self, pr_number, comments):
        self._pr_comments[pr_number] = comments

    def set_pr_reviews(self, pr_number, reviews):
        self._pr_reviews[pr_number] = reviews

    def set_pr_conversation_comments(self, pr_number, comments):
        self._pr_conversation_comments[pr_number] = comments

    def set_failed_checks(self, pr_number, checks):
        self._failed_checks[pr_number] = checks

    def set_workflow_runs(self, branch, sha, runs):
        self._workflow_runs[(branch, sha)] = runs

    def set_workflow_failure_logs(self, run_id, logs):
        self._workflow_failure_logs[run_id] = logs

    def set_default_branch(self, branch):
        self._default_branch = branch

    def set_reply_results(self, success):
        self._reply_results = success

    def set_workflow_completion_result(self, branch, sha, result):
        self._workflow_completion_results[(branch, sha)] = result

    def fetch_pr_comments(self, pr_number):
        self.calls.append(("fetch_pr_comments", pr_number))
        return self._pr_comments.get(pr_number, [])

    def fetch_pr_reviews(self, pr_number):
        self.calls.append(("fetch_pr_reviews", pr_number))
        return self._pr_reviews.get(pr_number, [])

    def fetch_pr_conversation_comments(self, pr_number):
        self.calls.append(("fetch_pr_conversation_comments", pr_number))
        return self._pr_conversation_comments.get(pr_number, [])

    def reply_to_review_comment(self, pr_number, comment_id, body):
        self.calls.append(("reply_to_review_comment", pr_number, comment_id, body))
        return self._reply_results

    def reply_to_pr_comment(self, pr_number, body):
        self.calls.append(("reply_to_pr_comment", pr_number, body))
        return self._reply_results

    def fetch_failed_checks(self, pr_number):
        self.calls.append(("fetch_failed_checks", pr_number))
        return self._failed_checks.get(pr_number, [])

    def get_workflow_runs_for_commit(self, branch, sha):
        self.calls.append(("get_workflow_runs_for_commit", branch, sha))
        return self._workflow_runs.get((branch, sha), [])

    def get_workflow_failure_logs(self, run_id):
        self.calls.append(("get_workflow_failure_logs", run_id))
        return self._workflow_failure_logs.get(run_id, "")

    def wait_for_workflow_completion(self, branch, sha, timeout_seconds=600):
        self.calls.append(("wait_for_workflow_completion", branch, sha))
        if (branch, sha) in self._workflow_completion_results:
            return self._workflow_completion_results[(branch, sha)]
        return (True, None)

    def get_default_branch(self):
        self.calls.append(("get_default_branch",))
        return self._default_branch
