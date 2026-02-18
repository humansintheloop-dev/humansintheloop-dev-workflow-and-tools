"""ModeFactory creates execution mode instances with their dependencies."""

from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.isolate_mode import IsolateMode, RealSubprocessRunner
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.worktree_mode import WorktreeMode


class ModeFactory:
    """Creates execution mode instances, wiring up their dependencies."""

    def __init__(self, opts, claude_runner, build_fixer_factory, project_initializer):
        self._opts = opts
        self._claude_runner = claude_runner
        self._build_fixer_factory = build_fixer_factory
        self._project_initializer = project_initializer

    def make_trunk_mode(self, git_repo, project):
        return TrunkMode(
            git_repo=git_repo,
            project=project,
            claude_runner=self._claude_runner,
        )

    def make_isolate_mode(self, repo, git_repo, project):
        return IsolateMode(
            repo=repo,
            git_repo=git_repo,
            project=project,
            project_initializer=self._project_initializer,
            subprocess_runner=RealSubprocessRunner(),
        )

    def make_worktree_mode(self, git_repo, project, state, work_plan_file):
        ci_monitor = GithubActionsMonitor(
            gh_client=git_repo.gh_client,
            skip_ci_wait=self._opts.skip_ci_wait,
            ci_timeout=self._opts.ci_timeout,
        )
        build_fixer = self._build_fixer_factory.create(git_repo)
        review_processor = PullRequestReviewProcessor(
            opts=self._opts,
            git_repo=git_repo,
            state=state,
            claude_runner=self._claude_runner,
        )
        return WorktreeMode(
            opts=self._opts,
            git_repo=git_repo,
            project=project,
            state=state,
            claude_runner=self._claude_runner,
            work_plan_file=work_plan_file,
            ci_monitor=ci_monitor,
            build_fixer=build_fixer,
            review_processor=review_processor,
        )
