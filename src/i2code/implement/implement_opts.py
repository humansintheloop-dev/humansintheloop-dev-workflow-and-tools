"""Options dataclass for the implement command."""

from dataclasses import dataclass

import click


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
    isolation_type: str | None = None
    isolated: bool = False
    trunk: bool = False
    dry_run: bool = False
    ignore_uncommitted_idea_changes: bool = False
    address_review_comments: bool = False

    _TRUNK_INCOMPATIBLE = [
        ("cleanup", "--cleanup"),
        ("setup_only", "--setup-only"),
        ("isolate", "--isolate"),
        ("isolated", "--isolated"),
        ("skip_ci_wait", "--skip-ci-wait"),
        ("address_review_comments", "--address-review-comments"),
    ]

    def validate_trunk_options(self):
        """Raise click.UsageError if --trunk is combined with incompatible options."""
        if not self.trunk:
            return
        incompatible = [flag for attr, flag in self._TRUNK_INCOMPATIBLE
                        if getattr(self, attr)]
        if self.ci_fix_retries != 3:
            incompatible.append("--ci-fix-retries")
        if self.ci_timeout != 600:
            incompatible.append("--ci-timeout")
        if incompatible:
            raise click.UsageError(
                f"--trunk cannot be combined with: {', '.join(incompatible)}"
            )
