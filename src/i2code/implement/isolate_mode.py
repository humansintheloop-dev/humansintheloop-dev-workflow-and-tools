"""IsolateMode: execute plan tasks by delegating to an isolarium VM."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from i2code.implement.managed_subprocess import ManagedSubprocess


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


def _find_i2code_src_dir():
    """Return the i2code source directory if running from an editable install."""
    try:
        path = Path(__file__).resolve()
        if "site-packages" in path.parts:
            return None
        for parent in path.parents:
            if (parent / "pyproject.toml").exists():
                return str(parent / "src")
    except OSError:
        pass
    return None


def _collect_value_flags(options):
    result = []
    for attr, flag, default in _VALUE_FLAGS:
        value = getattr(options, attr)
        if value != default:
            result.extend([flag, str(value)])
    return result


@dataclass
class WorktreeSetupDeps:
    """Dependencies for first-run worktree creation and scaffolding."""

    scaffolder_factory: object
    project_setup: object


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
        self._project_setup = worktree_setup.project_setup
        self._subprocess_runner = subprocess_runner

    def execute(self):
        """Create worktree, scaffold, clone, and launch isolarium — or reuse an existing clone.

        Returns:
            The subprocess return code from isolarium.
        """
        clone_repo = self._git_repo.find_clone(self._project.name)
        if clone_repo is not None:
            return self._launch_in_existing_clone(clone_repo)
        return self._setup_worktree_and_launch()

    def _launch_in_existing_clone(self, clone_repo):
        name, email = self._git_repo.get_user_config()
        clone_repo.set_user_config(name, email)
        self._project_setup.setup_clone(clone_repo)
        self._project = self._project.worktree_idea_project(
            clone_repo.working_tree_dir, self._git_repo.working_tree_dir,
        )
        return self._launch(cwd=clone_repo.working_tree_dir)

    def _setup_worktree_and_launch(self):
        idea_branch = self._git_repo.ensure_idea_branch(self._project.name)
        print(f"Idea branch: {idea_branch}")
        wt_git_repo = self._git_repo.ensure_worktree(self._project.name, idea_branch)
        wt_git_repo.set_upstream(idea_branch)
        print(f"Worktree: {wt_git_repo.working_tree_dir}")
        self._project_setup.setup_worktree(wt_git_repo)

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

        clone_repo = wt_git_repo.clone(self._project.name)
        self._project_setup.setup_clone(clone_repo)

        self._project = work_project.worktree_idea_project(
            clone_repo.working_tree_dir, wt_git_repo.working_tree_dir,
        )
        return self._launch(cwd=clone_repo.working_tree_dir)

    def _launch(self, cwd):
        cmd = self._build_isolarium_command(clone_dir=cwd)
        print(f"Running (cwd={cwd}): {' '.join(cmd)}")
        return self._subprocess_runner.run(cmd, cwd=cwd)

    def _build_isolarium_command(self, clone_dir):
        outer = self._build_outer_args()
        inner = self._build_inner_args(clone_dir)
        return outer + ["--"] + inner

    def _build_outer_args(self):
        args = ["isolarium", "--name", f"i2code-{self._project.name}"]
        if self._options.isolation_type is not None:
            args.extend(["--type", self._options.isolation_type])
        env_file = self._find_env_file()
        if env_file:
            args.extend(["--env-file", env_file])
        args.append("run")
        src_dir = _find_i2code_src_dir()
        if src_dir:
            args.extend(["--read", src_dir])
        if not self._options.non_interactive:
            args.append("--interactive")
        return args

    def _build_inner_args(self, clone_dir):
        rel_idea_dir = os.path.relpath(
            self._project.directory, clone_dir,
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
