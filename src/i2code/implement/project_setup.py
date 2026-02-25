"""Project setup: scaffolding and branch setup."""

import os
import sys
from typing import Optional

SCAFFOLDING_GUARD_DIR = ".hitl_dev"
SCAFFOLDING_GUARD_FILE = "scaffolding-done"


class ProjectScaffolder:
    """Orchestrates project scaffolding using injected dependencies."""

    def __init__(self, claude_runner, command_builder, git_repo=None, build_fixer=None, push_fn=None):
        self._claude_runner = claude_runner
        self._command_builder = command_builder
        self._git_repo = git_repo
        self._build_fixer = build_fixer
        self._push_fn = push_fn

    def ensure_scaffolding_setup(self, opts, idea_directory: str, branch: str) -> bool:
        """Ensure project scaffolding exists on the given branch.

        Returns True if setup succeeded (CI passes), False otherwise.
        """
        if self._guard_file_exists():
            return True

        self._git_repo.checkout(branch)

        head_before = self._git_repo.head_sha

        self.run_scaffolding(
            idea_directory,
            cwd=self._git_repo.working_tree_dir,
            interactive=not opts.non_interactive,
            mock_claude=opts.mock_claude,
        )

        head_advanced = self._git_repo.head_advanced_since(head_before)

        self._write_guard_file()

        self._push_fn(branch)
        
        if not head_advanced:
            return True

        if opts.skip_ci_wait:
            return True

        ci_success, failing_run = self._git_repo.gh_client.wait_for_workflow_completion(
            branch, self._git_repo.head_sha, timeout_seconds=opts.ci_timeout,
        )

        if not ci_success and failing_run:
            self._git_repo.branch = branch
            return self._build_fixer.fix_ci_failure()

        return ci_success

    def run_scaffolding(
        self, idea_directory: str, cwd: str,
        interactive: bool = True, mock_claude: Optional[str] = None,
    ):
        """Invoke Claude to generate project scaffolding."""
        cmd = self._command_builder.build_scaffolding_command(
            idea_directory, interactive=interactive, mock_claude=mock_claude,
        )
        result = self._claude_runner.run(cmd, cwd=cwd)

        if interactive or "<SUCCESS>" in result.output.stdout or "<NOTHING-TO-DO>" in result.output.stdout:
            return

        print("Error: Scaffolding failed.", file=sys.stderr)
        if result.diagnostics.error_message:
            print(f"  {result.diagnostics.error_message}", file=sys.stderr)
        if result.diagnostics.permission_denials:
            print(f"  Permission denied for {len(result.diagnostics.permission_denials)} action(s)", file=sys.stderr)
        for msg in result.diagnostics.last_messages:
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
