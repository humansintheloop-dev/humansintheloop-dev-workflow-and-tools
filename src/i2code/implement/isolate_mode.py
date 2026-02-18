"""IsolateMode: execute plan tasks by delegating to an isolarium VM."""

import os
import subprocess
import sys

from i2code.implement.project_setup import ensure_project_setup


class IsolateMode:
    """Execution mode that runs project setup on the host then delegates to isolarium VM.

    Args:
        repo: Git repository (for working_tree_dir and ensure_project_setup).
        git_repo: GitRepository for branch operations.
        project: IdeaProject with directory and name.
        gh_client: GitHubClient (or FakeGitHubClient) for PR/CI operations.
        project_setup: Object providing ensure_project_setup().
        subprocess_runner: Object providing run(cmd) -> returncode.
    """

    def __init__(self, repo, git_repo, project, gh_client, project_setup, subprocess_runner):
        self._repo = repo
        self._git_repo = git_repo
        self._project = project
        self._gh_client = gh_client
        self._project_setup = project_setup
        self._subprocess_runner = subprocess_runner

    def execute(
        self,
        non_interactive=False,
        mock_claude=None,
        cleanup=False,
        setup_only=False,
        extra_prompt=None,
        skip_ci_wait=False,
        ci_fix_retries=3,
        ci_timeout=600,
    ):
        """Run project setup on host, then delegate to isolarium VM.

        Returns:
            The subprocess return code from isolarium.
        """
        integration_branch = self._git_repo.ensure_integration_branch(
            self._project.name,
        )

        setup_ok = self._project_setup.ensure_project_setup(
            repo=self._repo,
            idea_directory=self._project.directory,
            idea_name=self._project.name,
            integration_branch=integration_branch,
            interactive=not non_interactive,
            mock_claude=mock_claude,
            ci_fix_retries=ci_fix_retries,
            ci_timeout=ci_timeout,
            skip_ci_wait=skip_ci_wait,
            gh_client=self._gh_client,
        )
        if not setup_ok:
            print("Error: Project scaffolding setup failed", file=sys.stderr)
            sys.exit(1)

        cmd = self._build_isolarium_command(
            non_interactive=non_interactive,
            mock_claude=mock_claude,
            cleanup=cleanup,
            setup_only=setup_only,
            extra_prompt=extra_prompt,
            skip_ci_wait=skip_ci_wait,
            ci_fix_retries=ci_fix_retries,
            ci_timeout=ci_timeout,
        )
        print(f"Running: {' '.join(cmd)}")
        return self._subprocess_runner.run(cmd)

    def _build_isolarium_command(
        self,
        non_interactive=False,
        mock_claude=None,
        cleanup=False,
        setup_only=False,
        extra_prompt=None,
        skip_ci_wait=False,
        ci_fix_retries=3,
        ci_timeout=600,
    ):
        rel_idea_dir = os.path.relpath(
            self._project.directory, self._repo.working_tree_dir,
        )

        isolarium_args = ["isolarium", "--name", f"i2code-{self._project.name}", "run"]
        if not non_interactive:
            isolarium_args.append("--interactive")

        cmd = isolarium_args + [
            "--", "i2code", "--with-sdkman", "implement", "--isolated", rel_idea_dir,
        ]

        if cleanup:
            cmd.append("--cleanup")
        if mock_claude:
            cmd.extend(["--mock-claude", mock_claude])
        if setup_only:
            cmd.append("--setup-only")
        if non_interactive:
            cmd.append("--non-interactive")
        if extra_prompt:
            cmd.extend(["--extra-prompt", extra_prompt])
        if skip_ci_wait:
            cmd.append("--skip-ci-wait")
        if ci_fix_retries != 3:
            cmd.extend(["--ci-fix-retries", str(ci_fix_retries)])
        if ci_timeout != 600:
            cmd.extend(["--ci-timeout", str(ci_timeout)])

        return cmd


class RealProjectSetup:
    """Delegates to the real ensure_project_setup function."""

    def ensure_project_setup(self, **kwargs):
        return ensure_project_setup(**kwargs)


class RealSubprocessRunner:
    """Delegates to the real subprocess.run."""

    def run(self, cmd):
        result = subprocess.run(cmd)
        return result.returncode
