"""Options dataclass for the implement command."""

from dataclasses import dataclass


@dataclass
class ImplementOpts:
    """All options for the implement command."""

    idea_directory: str
    cleanup: bool = False
    mock_claude: str | None = None
    setup_only: bool = False
    non_interactive: bool = False
    extra_prompt: str | None = None
    skip_ci_wait: bool = False
    ci_fix_retries: int = 3
    ci_timeout: int = 600
    isolate: bool = False
    isolated: bool = False
    trunk: bool = False
    dry_run: bool = False
    ignore_uncommitted_idea_changes: bool = False
