"""Git utility functions for the implement workflow."""

import subprocess


def get_default_branch() -> str:
    """Detect the default branch of the current GitHub repository.

    Uses `gh repo view` to query the default branch name.

    Returns:
        The default branch name (e.g., "main" or "master")

    Raises:
        RuntimeError: If the gh command fails
    """
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "defaultBranchRef", "--jq", ".defaultBranchRef.name"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to detect default branch: {result.stderr}")

    return result.stdout.strip()
