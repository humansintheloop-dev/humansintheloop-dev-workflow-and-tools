"""IsolateMode: execute plan tasks by delegating to an isolarium VM."""

import os
import subprocess
import sys
from dataclasses import dataclass

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


def _collect_value_flags(options):
    result = []
    for attr, flag, default in _VALUE_FLAGS:
        value = getattr(options, attr)
        if value != default:
            result.extend([flag, str(value)])
    return result


@dataclass
class IsolateOptions:
    """Options for IsolateMode.execute()."""

    non_interactive: bool = False
    mock_claude: str = None
    cleanup: bool = False
    setup_only: bool = False
    extra_prompt: str = None
    skip_ci_wait: bool = False
    ci_fix_retries: int = 3
    ci_timeout: int = 600
    isolation_type: str = None


class IsolateMode:
    """Execution mode that runs project setup on the host then delegates to isolarium VM.

    Args:
        git_repo: GitRepository for branch and working-tree operations.
        project: IdeaProject with directory and name.
        project_initializer: ProjectInitializer providing ensure_project_setup().
        subprocess_runner: Object providing run(cmd) -> returncode.
    """

    def __init__(self, git_repo, project, project_initializer, subprocess_runner):
        self._git_repo = git_repo
        self._project = project
        self._project_initializer = project_initializer
        self._subprocess_runner = subprocess_runner

    def execute(self, options=None):
        """Run project setup on host, then delegate to isolarium VM.

        Returns:
            The subprocess return code from isolarium.
        """
        if options is None:
            options = IsolateOptions()
        idea_branch = f"idea/{self._project.name}"

        setup_ok = self._project_initializer.ensure_project_setup(
            idea_directory=self._project.directory,
            branch=idea_branch,
            interactive=not options.non_interactive,
            mock_claude=options.mock_claude,
            ci_timeout=options.ci_timeout,
            skip_ci_wait=options.skip_ci_wait,
        )
        if not setup_ok:
            print("Error: Project scaffolding setup failed", file=sys.stderr)
            sys.exit(1)

        cmd = self._build_isolarium_command(options)
        print(f"Running: {' '.join(cmd)}")
        return self._subprocess_runner.run(cmd, cwd=self._git_repo.working_tree_dir)

    def _build_isolarium_command(self, options):
        outer = self._build_outer_args(options)
        inner = self._build_inner_args(options)
        return outer + ["--"] + inner

    def _build_outer_args(self, options):
        args = ["isolarium", "--name", f"i2code-{self._project.name}"]
        if options.isolation_type is not None:
            args.extend(["--type", options.isolation_type])
        env_file = self._find_env_file()
        if env_file:
            args.extend(["--env-file", env_file])
        args.append("run")
        if not options.non_interactive:
            args.append("--interactive")
        return args

    def _build_inner_args(self, options):
        rel_idea_dir = os.path.relpath(
            self._project.directory, self._git_repo.working_tree_dir,
        )
        args = ["i2code", "--with-sdkman", "implement", "--isolated", rel_idea_dir]
        args.extend(flag for attr, flag in _BOOL_FLAGS if getattr(options, attr))
        args.extend(_collect_value_flags(options))
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
