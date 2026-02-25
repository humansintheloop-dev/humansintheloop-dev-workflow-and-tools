"""IsolateMode: execute plan tasks by delegating to an isolarium VM."""

import os
import subprocess
import sys

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


class IsolateMode:
    """Execution mode that runs project setup on the host then delegates to isolarium VM.

    Args:
        workspace: Workspace bundling git_repo and project.
        project_scaffolder: ProjectScaffolder providing ensure_scaffolding_setup().
        subprocess_runner: Object providing run(cmd) -> returncode.
        clone_creator: Object providing create_clone(source_path, idea_name, origin_url).
    """

    def __init__(self, workspace, project_scaffolder, subprocess_runner, clone_creator):
        self._git_repo = workspace.git_repo
        self._project = workspace.project
        self._project_scaffolder = project_scaffolder
        self._subprocess_runner = subprocess_runner
        self._clone_creator = clone_creator

    def execute(self, options):
        """Run project setup on host (because host token can configure Github Actions workflow files), then delegate to Isolarium

        Returns:
            The subprocess return code from isolarium.
        """
        idea_branch = f"idea/{self._project.name}"

        setup_ok = self._project_scaffolder.ensure_scaffolding_setup(
            options, idea_directory=self._project.directory, branch=idea_branch,
        )
        if not setup_ok:
            print("Error: Project scaffolding setup failed", file=sys.stderr)
            sys.exit(1)

        clone_path = self._clone_creator.create_clone(
            source_path=self._git_repo.working_tree_dir,
            idea_name=self._project.name,
            origin_url=self._git_repo.origin_url,
        )

        cmd = self._build_isolarium_command(options)
        print(f"Running: {' '.join(cmd)}")
        return self._subprocess_runner.run(cmd, cwd=clone_path)

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
