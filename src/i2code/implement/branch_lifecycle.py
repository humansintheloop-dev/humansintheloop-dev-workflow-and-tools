"""Branch lifecycle: rebase, cleanup, interrupt handling."""

import signal
import subprocess
import sys


# Main Branch Advancement Functions

def has_main_advanced(original_head: str, current_head: str) -> bool:
    """Check if the main branch has advanced since we started."""
    return original_head != current_head


def get_remote_main_head(branch: str, remote: str = "origin") -> str:
    """Get the current HEAD SHA of the remote main branch."""
    subprocess.run(
        ["git", "fetch", remote, branch],
        capture_output=True, text=True,
    )
    result = subprocess.run(
        ["git", "ls-remote", remote, f"refs/heads/{branch}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    return result.stdout.split()[0]


def rebase_integration_branch(integration_branch: str, base_branch: str) -> bool:
    """Attempt to rebase the integration branch onto the updated main."""
    subprocess.run(
        ["git", "checkout", integration_branch],
        capture_output=True, text=True,
    )
    result = subprocess.run(
        ["git", "rebase", f"origin/{base_branch}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "rebase", "--abort"],
            capture_output=True, text=True,
        )
        return False
    return True


def update_slice_after_rebase(slice_branch: str) -> bool:
    """Force push the slice branch after a successful rebase."""
    result = subprocess.run(
        ["git", "push", "--force-with-lease", "origin", slice_branch],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def get_rebase_conflict_message(integration_branch: str, base_branch: str) -> str:
    """Generate a message explaining rebase conflict and how to resolve it."""
    return f"""
Rebase conflict detected on {integration_branch}!

The main branch has advanced and there are conflicts that require manual resolution.

To resolve:
1. Navigate to the worktree directory
2. Run: git rebase origin/{base_branch}
3. Resolve the conflicts in each file
4. Run: git add <resolved-files>
5. Run: git rebase --continue
6. Re-run this script to continue

The script will now pause. Press Enter when ready to exit, or Ctrl+C to abort.
"""


# Cleanup Functions

def remove_worktree(worktree_path: str) -> bool:
    """Remove a git worktree."""
    result = subprocess.run(
        ["git", "worktree", "remove", worktree_path],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def delete_local_branch(branch_name: str) -> bool:
    """Delete a local git branch."""
    result = subprocess.run(
        ["git", "branch", "-D", branch_name],
        capture_output=True, text=True,
    )
    return result.returncode == 0


# Interrupt Handling

_interrupt_state = {
    "state_file": None,
    "state": None,
}


def register_signal_handlers():
    """Register signal handlers for graceful shutdown."""
    signal.signal(signal.SIGINT, _handle_interrupt)


def _handle_interrupt(signum, frame):
    """Internal handler for SIGINT signal."""
    print("\nInterrupted! Saving state...")
    if _interrupt_state["state_file"] and _interrupt_state["state"]:
        cleanup_on_interrupt(
            _interrupt_state["state_file"],
            _interrupt_state["state"],
        )
    sys.exit(1)


def cleanup_on_interrupt(state_file: str, state) -> None:
    """Clean up and save state when interrupted."""
    state.save()
    print("State saved. You can resume by running the script again.")
