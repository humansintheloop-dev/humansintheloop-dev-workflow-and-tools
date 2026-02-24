"""Branch lifecycle: rebase and cleanup."""

import subprocess


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
