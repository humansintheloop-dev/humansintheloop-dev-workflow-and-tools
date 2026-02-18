"""ImplementCommand encapsulates the implement workflow logic."""

import sys

from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.github_actions_monitor import GithubActionsMonitor
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.workflow_state import WorkflowState
from i2code.implement.git_setup import (
    validate_idea_files_committed,
    ensure_claude_permissions,
    get_next_task,
)
from i2code.implement.isolate_mode import IsolateMode, RealProjectSetup, RealSubprocessRunner
from i2code.implement.trunk_mode import TrunkMode
from i2code.implement.worktree_mode import WorktreeMode


class ImplementCommand:
    """Orchestrates the implement workflow across trunk, isolate, and worktree modes."""

    def __init__(self, opts, project, repo, git_repo, claude_runner, gh_client):
        self.opts = opts
        self.project = project
        self.repo = repo
        self.git_repo = git_repo
        self.claude_runner = claude_runner
        self.gh_client = gh_client

    def execute(self):
        """Implement a development plan using Git worktrees and GitHub Draft PRs."""
        self.project.validate()
        self.project.validate_files()

        if self.opts.dry_run:
            if self.opts.trunk:
                mode = "trunk"
            elif self.opts.isolate:
                mode = "isolate"
            else:
                mode = "worktree"
            print(f"Mode: {mode}")
            print(f"Idea: {self.project.name}")
            print(f"Directory: {self.project.directory}")
            return

        if not self.opts.isolated and not self.opts.ignore_uncommitted_idea_changes:
            validate_idea_files_committed(self.project)

        if self.opts.trunk:
            self._trunk_mode()
        elif self.opts.isolate:
            self._isolate_mode()
        else:
            self._worktree_mode()

    def _trunk_mode(self):
        """Execute tasks locally on the current branch."""
        self.opts.validate_trunk_options()

        trunk_mode = TrunkMode(
            git_repo=self.git_repo,
            project=self.project,
            claude_runner=self.claude_runner,
        )
        trunk_mode.execute(
            non_interactive=self.opts.non_interactive,
            mock_claude=self.opts.mock_claude,
            extra_prompt=self.opts.extra_prompt,
        )

    def _isolate_mode(self):
        """Delegate execution to an isolarium VM."""
        isolate_mode = IsolateMode(
            repo=self.repo,
            git_repo=self.git_repo,
            project=self.project,
            gh_client=self.gh_client,
            project_setup=RealProjectSetup(),
            subprocess_runner=RealSubprocessRunner(),
        )
        returncode = isolate_mode.execute(
            non_interactive=self.opts.non_interactive,
            mock_claude=self.opts.mock_claude,
            cleanup=self.opts.cleanup,
            setup_only=self.opts.setup_only,
            extra_prompt=self.opts.extra_prompt,
            skip_ci_wait=self.opts.skip_ci_wait,
            ci_fix_retries=self.opts.ci_fix_retries,
            ci_timeout=self.opts.ci_timeout,
        )
        sys.exit(returncode)

    def _worktree_mode(self):
        """Execute tasks using worktree + PR + CI loop."""
        state = WorkflowState.load(self.project.state_file)

        integration_branch = self.git_repo.ensure_integration_branch(
            self.project.name, isolated=self.opts.isolated
        )
        print(f"Integration branch: {integration_branch}")

        next_task = get_next_task(self.project.plan_file)
        first_task_name = next_task.task.title if next_task else "implementation"

        slice_branch = self.git_repo.ensure_slice_branch(
            self.project.name, state.slice_number, first_task_name, integration_branch
        )
        print(f"Slice branch: {slice_branch}")

        if self.opts.isolated:
            self.repo.config_writer().set_value("user", "email", "test@test.com").release()
            self.repo.config_writer().set_value("user", "name", "Test User").release()
            ensure_claude_permissions(self.git_repo.working_tree_dir)
            work_plan_file = self.project.plan_file
            self.git_repo.checkout(slice_branch)
        else:
            self.git_repo = self.git_repo.ensure_worktree(self.project.name, integration_branch)
            print(f"Worktree: {self.git_repo.working_tree_dir}")
            ensure_claude_permissions(self.git_repo.working_tree_dir)
            work_project = self.project.worktree_idea_project(
                self.git_repo.working_tree_dir, self.repo.working_tree_dir
            )
            work_plan_file = work_project.plan_file
            self.git_repo.checkout(slice_branch)

        self.git_repo.branch = slice_branch

        if self.opts.setup_only:
            print("Setup complete. Exiting (--setup-only mode).")
            return

        existing_pr = self.gh_client.find_pr(slice_branch)
        if existing_pr:
            self.git_repo.pr_number = existing_pr
            print(f"Reusing existing PR #{existing_pr}")

        ci_monitor = GithubActionsMonitor(
            gh_client=self.gh_client,
            skip_ci_wait=self.opts.skip_ci_wait,
            ci_timeout=self.opts.ci_timeout,
        )

        build_fixer = GithubActionsBuildFixer(
            opts=self.opts,
            git_repo=self.git_repo,
            claude_runner=self.claude_runner,
        )

        review_processor = PullRequestReviewProcessor(
            opts=self.opts,
            git_repo=self.git_repo,
            state=state,
            claude_runner=self.claude_runner,
        )

        worktree_mode = WorktreeMode(
            opts=self.opts,
            git_repo=self.git_repo,
            project=self.project,
            state=state,
            claude_runner=self.claude_runner,
            work_plan_file=work_plan_file,
            ci_monitor=ci_monitor,
            build_fixer=build_fixer,
            review_processor=review_processor,
        )
        worktree_mode.execute()
