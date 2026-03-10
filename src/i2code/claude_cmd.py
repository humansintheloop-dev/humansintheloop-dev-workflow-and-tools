"""Shared utilities for building claude CLI commands."""


def build_allowed_tools_flag(repo_root: str, idea_dir: str) -> str:
    """Build the --allowedTools flag value for claude CLI.

    Returns a comma-separated string granting Read access to the repo root
    and Write/Edit access to the idea directory.
    """
    return (
        f"Read({repo_root}/),"
        f"Write({idea_dir}/),"
        f"Edit({idea_dir}/)"
    )
