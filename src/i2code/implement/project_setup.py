"""Project setup: scaffolding and branch setup."""

import os
import sys
from dataclasses import dataclass
from typing import Optional

SCAFFOLDING_GUARD_DIR = ".hitl_dev"
SCAFFOLDING_GUARD_FILE = "scaffolding-done"


@dataclass
class ScaffoldingSteps:
    """Bundles the runner, fixer, and push function used during scaffolding."""
    claude_runner: object
    build_fixer: object
    push_fn: object


class ScaffoldingCreator:
    """Invokes Claude to generate project scaffolding."""

    def __init__(self, command_builder, claude_runner):
        self._command_builder = command_builder
        self._claude_runner = claude_runner

    def run_scaffolding(
        self, idea_directory: str, cwd: str,
        interactive: bool = True, mock_claude: Optional[str] = None,
    ):
        """Invoke Claude to generate project scaffolding."""
        cmd = self._command_builder.build_scaffolding_command(
            idea_directory, interactive=interactive, mock_claude=mock_claude,
        )
        result = self._claude_runner.run(cmd, cwd=cwd)

        if interactive or _scaffolding_succeeded(result):
            return

        _print_scaffolding_failure(result.diagnostics)
        sys.exit(1)


class ProjectScaffolder:
    """Orchestrates project scaffolding using injected dependencies."""

    def __init__(self, scaffolding_creator, steps, git_repo):
        self._scaffolding_creator = scaffolding_creator
        self._git_repo = git_repo
        self._steps = steps

    def ensure_scaffolding_setup(self, opts, idea_directory: str, branch: str) -> bool:
        """Ensure project scaffolding exists on the given branch.

        Returns True if setup succeeded (CI passes), False otherwise.
        """
        if self._guard_file_exists():
            return True

        self._git_repo.checkout(branch)

        head_before = self._git_repo.head_sha

        self._scaffolding_creator.run_scaffolding(
            idea_directory,
            cwd=self._git_repo.working_tree_dir,
            interactive=not opts.non_interactive,
            mock_claude=opts.mock_claude,
        )

        head_advanced = self._git_repo.head_advanced_since(head_before)

        self._write_guard_file()

        self._steps.push_fn(branch)

        if not head_advanced:
            return True

        if opts.skip_ci_wait:
            return True

        ci_success, failing_run = self._git_repo.gh_client.wait_for_workflow_completion(
            branch, self._git_repo.head_sha, timeout_seconds=opts.ci_timeout,
        )

        if not ci_success and failing_run:
            self._git_repo.branch = branch
            return self._steps.build_fixer.fix_ci_failure()

        return ci_success

    def _guard_file_path(self):
        hitl_dir = os.path.join(self._git_repo.working_tree_dir, SCAFFOLDING_GUARD_DIR)
        return os.path.join(hitl_dir, SCAFFOLDING_GUARD_FILE)

    def _guard_file_exists(self):
        return os.path.isfile(self._guard_file_path())

    def _write_guard_file(self):
        guard_file = self._guard_file_path()
        os.makedirs(os.path.dirname(guard_file), exist_ok=True)
        open(guard_file, "w").close()
        self._git_repo.add_and_commit(guard_file, "Mark scaffolding complete")


# --- Private helpers used by ScaffoldingCreator ---

_SUCCESS_TAGS = ("<SUCCESS>", "<NOTHING-TO-DO>")


def _scaffolding_succeeded(result):
    return any(tag in result.output.stdout for tag in _SUCCESS_TAGS)


def _print_scaffolding_failure(diagnostics):
    print("Error: Scaffolding failed.", file=sys.stderr)
    if diagnostics.error_message:
        print(f"  {diagnostics.error_message}", file=sys.stderr)
    if diagnostics.permission_denials:
        print(f"  Permission denied for {len(diagnostics.permission_denials)} action(s)", file=sys.stderr)
    for msg in diagnostics.last_messages:
        _print_diagnostic_message(msg)


def _print_diagnostic_message(msg):
    msg_type = msg.get('type', 'unknown')
    if msg_type == 'assistant':
        _print_assistant_text(msg)
    elif msg_type == 'result':
        text = msg.get('result', '')
        if text:
            print(f"  Result: {text}", file=sys.stderr)


def _print_assistant_text(msg):
    for item in msg.get('message', {}).get('content', []):
        if item.get('type') == 'text':
            print(f"  Claude: {item['text']}", file=sys.stderr)
