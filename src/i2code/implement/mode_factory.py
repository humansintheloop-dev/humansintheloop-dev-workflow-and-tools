"""ModeFactory creates execution mode instances with their dependencies."""

from i2code.implement.command_builder import CommandBuilder
from i2code.implement.commit_recovery import TaskCommitRecovery
from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.isolate_mode import IsolateMode, SubprocessRunner, WorktreeSetupDeps
from i2code.implement.pr_helpers import push_branch_to_remote
from i2code.implement.project_scaffolding import ProjectScaffolder, ScaffoldingCreator, ScaffoldingSteps
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.workspace import Workspace
from i2code.implement.worktree_mode import LoopSteps, WorktreeMode
from i2code.implement.worktree_setup import setup_project


class ModeFactory:
    """Creates execution mode instances, wiring up their dependencies."""

    def __init__(self, opts, claude_runner, build_fixer_factory):
        self._opts = opts
        self._claude_runner = claude_runner
        self._build_fixer_factory = build_fixer_factory

    def make_trunk_mode(self, git_repo, project):
        workspace = Workspace(git_repo=git_repo, project=project)
        commit_recovery = TaskCommitRecovery(
            git_repo=git_repo,
            project=project,
            claude_runner=self._claude_runner,
        )
        return TrunkMode(
            opts=self._opts,
            workspace=workspace,
            claude_runner=self._claude_runner,
            commit_recovery=commit_recovery,
        )

    def make_isolate_mode(self, git_repo, project, opts):
        scaffolding_creator = ScaffoldingCreator(
            command_builder=CommandBuilder(),
            claude_runner=self._claude_runner,
        )

        def scaffolder_factory(wt_git_repo):
            steps = ScaffoldingSteps(
                claude_runner=self._claude_runner,
                build_fixer=self._build_fixer_factory.create(wt_git_repo),
                push_fn=push_branch_to_remote,
            )
            return ProjectScaffolder(
                scaffolding_creator=scaffolding_creator,
                git_repo=wt_git_repo,
                steps=steps,
            )

        workspace = Workspace(git_repo=git_repo, project=project)
        worktree_setup = WorktreeSetupDeps(
            scaffolder_factory=scaffolder_factory,
            project_setup_fn=setup_project,
        )
        return IsolateMode(
            workspace=workspace,
            options=opts,
            worktree_setup=worktree_setup,
            subprocess_runner=SubprocessRunner(),
        )

    def make_worktree_mode(self, git_repo, state, work_project):
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
        commit_recovery = TaskCommitRecovery(
            git_repo=git_repo,
            project=work_project,
            claude_runner=self._claude_runner,
        )
        loop_steps = LoopSteps(
            claude_runner=self._claude_runner,
            state=state,
            ci_monitor=ci_monitor,
            build_fixer=build_fixer,
            review_processor=review_processor,
            commit_recovery=commit_recovery,
        )
        return WorktreeMode(
            opts=self._opts,
            git_repo=git_repo,
            work_project=work_project,
            loop_steps=loop_steps,
        )
