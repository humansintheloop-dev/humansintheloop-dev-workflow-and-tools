"""IsolateMode: execute plan tasks by delegating to an isolarium VM."""

import os
import subprocess
import sys
from dataclasses import dataclass

from i2code.implement.managed_subprocess import ManagedSubprocess
from i2code.implement.repo_cloner import clone_path_for


_BOOL_FLAGS = [
    ("cleanup", "--cleanup"),
    ("setup_only", "--setup-only"),
    ("non_interactive", "--non-interactive"),
    ("skip_ci_wait", "--skip-ci-wait"),
]

_VALUE_FLAGS = [
    ("mock_claude", "--mock-claude", None),
    ("extra_prompt", "--extra-prompt", None),
    ("ci_fix_retries", "--ci-fix-retries", 3),
    ("ci_timeout", "--ci-timeout", 600),
]


def _collect_value_flags(options):
    result = []
    for attr, flag, default in _VALUE_FLAGS:
        value = getattr(options, attr)
        if value != default:
            result.extend([flag, str(value)])
    return result


@dataclass
class WorktreeSetupDeps:
    """Dependencies for first-run worktree creation, scaffolding, and cloning."""

    scaffolder_factory: object
    clone_creator: object
    project_setup_fn: object


class IsolateMode:
    """Execution mode that runs project setup on the host then delegates to isolarium VM.

    Args:
        workspace: Workspace bundling git_repo and project.
        options: ImplementOpts with flags for the isolarium command.
        worktree_setup: WorktreeSetupDeps for first-run setup.
        subprocess_runner: Object providing run(cmd) -> returncode.
    """

    def __init__(self, workspace, options, worktree_setup, subprocess_runner):
        self._git_repo = workspace.git_repo
        self._project = workspace.project
        self._options = options
        self._scaffolder_factory = worktree_setup.scaffolder_factory
        self._clone_creator = worktree_setup.clone_creator
        self._project_setup_fn = worktree_setup.project_setup_fn
        self._subprocess_runner = subprocess_runner

    def execute(self):
        """Create worktree, scaffold, clone, and launch isolarium — or reuse an existing clone.

        Returns:
            The subprocess return code from isolarium.
        """
        clone_path = clone_path_for(self._git_repo.working_tree_dir, self._project.name)
        if os.path.isdir(clone_path):
            return self._launch_in_existing_clone(clone_path)
        return self._setup_worktree_and_launch()

    def _launch_in_existing_clone(self, clone_path):
        self._project = self._project.worktree_idea_project(
            clone_path, self._git_repo.working_tree_dir,
        )
        return self._launch(cwd=clone_path)

    def _setup_worktree_and_launch(self):
        idea_branch = self._git_repo.ensure_idea_branch(self._project.name)
        print(f"Idea branch: {idea_branch}")
        wt_git_repo = self._git_repo.ensure_worktree(self._project.name, idea_branch)
        wt_git_repo.set_upstream(idea_branch)
        print(f"Worktree: {wt_git_repo.working_tree_dir}")
        self._project_setup_fn(wt_git_repo)

        work_project = self._project.worktree_idea_project(
            wt_git_repo.working_tree_dir, wt_git_repo.main_repo_dir,
        )

        scaffolder = self._scaffolder_factory(wt_git_repo)
        setup_ok = scaffolder.ensure_scaffolding_setup(
            self._options, idea_directory=work_project.directory,
            branch=f"idea/{self._project.name}",
        )
        if not setup_ok:
            print("Error: Project scaffolding setup failed", file=sys.stderr)
            sys.exit(1)

        clone_path = self._clone_creator.create_clone(
            source_path=wt_git_repo.working_tree_dir,
            idea_name=self._project.name,
            origin_url=wt_git_repo.origin_url,
            clone_base=self._git_repo.working_tree_dir,
        )

        self._git_repo = wt_git_repo
        self._project = work_project
        return self._launch(cwd=clone_path)

    def _launch(self, cwd):
        cmd = self._build_isolarium_command()
        print(f"Running: {' '.join(cmd)}")
        return self._subprocess_runner.run(cmd, cwd=cwd)

    def _build_isolarium_command(self):
        outer = self._build_outer_args()
        inner = self._build_inner_args()
        return outer + ["--"] + inner

    def _build_outer_args(self):
        args = ["isolarium", "--name", f"i2code-{self._project.name}"]
        if self._options.isolation_type is not None:
            args.extend(["--type", self._options.isolation_type])
        env_file = self._find_env_file()
        if env_file:
            args.extend(["--env-file", env_file])
        args.append("run")
        if not self._options.non_interactive:
            args.append("--interactive")
        return args

    def _build_inner_args(self):
        rel_idea_dir = os.path.relpath(
            self._project.directory, self._git_repo.working_tree_dir,
        )
        args = ["i2code", "--with-sdkman", "implement", "--isolated", rel_idea_dir]
        args.extend(flag for attr, flag in _BOOL_FLAGS if getattr(self._options, attr))
        args.extend(_collect_value_flags(self._options))
        return args

    def _find_env_file(self):
        """Return path to .env.local in the main repo, or None if not found."""
        env_file = os.path.join(self._git_repo.main_repo_dir, ".env.local")
        if os.path.isfile(env_file):
            return env_file
        return None


class SubprocessRunner:
    """Runs subprocess with ManagedSubprocess for clean interrupt handling."""

    def run(self, cmd, cwd=None):
        process = subprocess.Popen(cmd, start_new_session=True, cwd=cwd)
        with ManagedSubprocess(process, label="isolarium") as managed:
            process.wait()
        if managed.interrupted:
            return 130
        return process.returncode
