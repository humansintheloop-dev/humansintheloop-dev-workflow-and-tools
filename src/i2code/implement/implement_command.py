"""ImplementCommand encapsulates the implement workflow logic."""

import sys

from i2code.implement.isolate_mode import IsolateOptions
from i2code.implement.workflow_state import WorkflowState
from i2code.implement.git_setup import validate_idea_files_committed
from i2code.implement.worktree_setup import setup_project


class ImplementCommand:
    """Orchestrates the implement workflow across trunk, isolate, and worktree modes."""

    def __init__(self, opts, project, git_repo, mode_factory):
        self.opts = opts
        self.project = project
        self.git_repo = git_repo
        self.mode_factory = mode_factory

    def execute(self):
        """Implement a development plan using Git worktrees and GitHub Draft PRs."""
        self._validate_and_apply_defaults()

        if self.opts.dry_run:
            self._print_dry_run()
            return

        self._check_idea_files_committed()

        if self._all_tasks_already_complete():
            return

        self._dispatch_mode()

    def _validate_and_apply_defaults(self):
        self.project.validate()
        self.project.validate_files()
        if self.opts.isolation_type:
            self.opts.isolate = True

    def _check_idea_files_committed(self):
        if not self.opts.isolated and not self.opts.ignore_uncommitted_idea_changes:
            validate_idea_files_committed(self.project)

    def _dispatch_mode(self):
        if self.opts.trunk:
            self._trunk_mode()
        elif self.opts.isolate:
            self._isolate_mode()
        else:
            self._worktree_mode()

    def _all_tasks_already_complete(self):
        if self.project.get_next_task() is None:
            print("All tasks are already complete.")
            return True
        return False

    def _all_tasks_already_complete_in_worktree(self):
        if self.project.get_next_task() is None:
            print("All tasks are already complete in worktree.")
            return True
        return False

    def _print_dry_run(self):
        """Print configuration summary without executing."""
        if self.opts.trunk:
            mode = "trunk"
        elif self.opts.isolate:
            mode = "isolate"
        else:
            mode = "worktree"
        print(f"Mode: {mode}")
        print(f"Idea: {self.project.name}")
        print(f"Directory: {self.project.directory}")

    def _trunk_mode(self):
        """Execute tasks locally on the current branch."""
        self.opts.validate_trunk_options()

        trunk_mode = self.mode_factory.make_trunk_mode(
            git_repo=self.git_repo,
            project=self.project,
        )
        trunk_mode.execute(
            non_interactive=self.opts.non_interactive,
            mock_claude=self.opts.mock_claude,
            extra_prompt=self.opts.extra_prompt,
        )

    def _isolate_mode(self):
        """Delegate execution to an isolarium VM."""
        idea_branch = self.git_repo.ensure_idea_branch(self.project.name)
        print(f"Idea branch: {idea_branch}")
        self.git_repo = self.git_repo.ensure_worktree(self.project.name, idea_branch)
        self.git_repo.set_upstream(idea_branch)
        print(f"Worktree: {self.git_repo.working_tree_dir}")
        main_repo_dir = self.git_repo.main_repo_dir
        setup_project(self.git_repo.working_tree_dir, source_root=main_repo_dir)
        work_project = self.project.worktree_idea_project(
            self.git_repo.working_tree_dir, main_repo_dir
        )

        isolate_mode = self.mode_factory.make_isolate_mode(
            git_repo=self.git_repo,
            project=work_project,
        )
        options = IsolateOptions(
            non_interactive=self.opts.non_interactive,
            mock_claude=self.opts.mock_claude,
            cleanup=self.opts.cleanup,
            setup_only=self.opts.setup_only,
            extra_prompt=self.opts.extra_prompt,
            skip_ci_wait=self.opts.skip_ci_wait,
            ci_fix_retries=self.opts.ci_fix_retries,
            ci_timeout=self.opts.ci_timeout,
            isolation_type=self.opts.isolation_type,
        )
        returncode = isolate_mode.execute(options)
        sys.exit(returncode)

    def _worktree_mode(self):
        """Execute tasks using worktree + PR + CI loop."""
        if self._all_tasks_already_complete_in_worktree():
            return

        state = WorkflowState.load(self.project.state_file)

        idea_branch = self.git_repo.ensure_idea_branch(self.project.name)
        print(f"Idea branch: {idea_branch}")

        if self.opts.isolated:
            print(f"Worktree: {self.git_repo.working_tree_dir}")
            self.git_repo.set_user_config("Test User", "test@test.com")
            setup_project(self.git_repo.working_tree_dir)
            work_project = self.project
        else:
            main_repo_dir = self.git_repo.working_tree_dir
            self.git_repo = self.git_repo.ensure_worktree(self.project.name, idea_branch)
            print(f"Worktree: {self.git_repo.working_tree_dir}")
            setup_project(self.git_repo.working_tree_dir, source_root=main_repo_dir)
            work_project = self.project.worktree_idea_project(
                self.git_repo.working_tree_dir, main_repo_dir
            )

        self.git_repo.branch = idea_branch

        if self.opts.setup_only:
            print("Setup complete. Exiting (--setup-only mode).")
            return

        existing_pr = self.git_repo.gh_client.find_pr(idea_branch)
        if existing_pr:
            self.git_repo.pr_number = existing_pr
            print(f"Reusing existing PR #{existing_pr}")

        worktree_mode = self.mode_factory.make_worktree_mode(
            git_repo=self.git_repo,
            state=state,
            work_project=work_project,
        )
        worktree_mode.execute()
