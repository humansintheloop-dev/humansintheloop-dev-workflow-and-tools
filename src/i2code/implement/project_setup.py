"""Project setup: scaffolding and integration branch setup."""

import sys
from typing import Optional

from git import Repo

from i2code.implement.claude_runner import RealClaudeRunner
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.git_repository import GitRepository
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixer
from i2code.implement.github_client import GitHubClient
from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.pr_helpers import push_branch_to_remote


def ensure_project_setup(
    repo: Repo,
    idea_directory: str,
    idea_name: str,
    integration_branch: str,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    ci_fix_retries: int = 3,
    ci_timeout: int = 600,
    skip_ci_wait: bool = False,
    gh_client=None,
) -> bool:
    """Ensure project scaffolding exists on the integration branch.

    Returns True if setup succeeded (CI passes), False otherwise.
    """
    if gh_client is None:
        gh_client = GitHubClient()

    repo.git.checkout(integration_branch)

    head_before = repo.head.commit.hexsha

    initializer = ProjectInitializer(
        claude_runner=RealClaudeRunner(),
        command_builder=CommandBuilder(),
    )
    initializer.run_scaffolding(idea_directory, cwd=repo.working_tree_dir, interactive=interactive, mock_claude=mock_claude)

    head_after = repo.head.commit.hexsha

    if head_before == head_after:
        return True

    push_branch_to_remote(integration_branch)

    if skip_ci_wait:
        return True

    ci_success, failing_run = gh_client.wait_for_workflow_completion(
        integration_branch, head_after, timeout_seconds=ci_timeout
    )

    if not ci_success and failing_run:
        git_repo = GitRepository(repo, gh_client)
        git_repo.branch = integration_branch
        opts = ImplementOpts(
            idea_directory="",
            non_interactive=not interactive,
            mock_claude=mock_claude,
            ci_fix_retries=ci_fix_retries,
        )
        build_fixer = GithubActionsBuildFixer(opts, git_repo, RealClaudeRunner())
        return build_fixer.fix_ci_failure()

    return ci_success


class ProjectInitializer:
    """Orchestrates project scaffolding using injected dependencies."""

    def __init__(self, claude_runner, command_builder, git_repo=None, build_fixer=None, push_fn=None):
        self._claude_runner = claude_runner
        self._command_builder = command_builder
        self._git_repo = git_repo
        self._build_fixer = build_fixer
        self._push_fn = push_fn

    def run_scaffolding(
        self, idea_directory: str, cwd: str,
        interactive: bool = True, mock_claude: Optional[str] = None,
    ):
        """Invoke Claude to generate project scaffolding."""
        cmd = self._command_builder.build_scaffolding_command(
            idea_directory, interactive=interactive, mock_claude=mock_claude,
        )
        if interactive:
            result = self._claude_runner.run_interactive(cmd, cwd=cwd)
        else:
            result = self._claude_runner.run_with_capture(cmd, cwd=cwd)

        if interactive or "<SUCCESS>" in result.stdout or "<NOTHING-TO-DO>" in result.stdout:
            return

        print("Error: Scaffolding failed.", file=sys.stderr)
        if result.error_message:
            print(f"  {result.error_message}", file=sys.stderr)
        if result.permission_denials:
            print(f"  Permission denied for {len(result.permission_denials)} action(s)", file=sys.stderr)
        for msg in result.last_messages:
            msg_type = msg.get('type', 'unknown')
            if msg_type == 'assistant':
                for item in msg.get('message', {}).get('content', []):
                    if item.get('type') == 'text':
                        print(f"  Claude: {item['text']}", file=sys.stderr)
            elif msg_type == 'result':
                text = msg.get('result', '')
                if text:
                    print(f"  Result: {text}", file=sys.stderr)
        sys.exit(1)


