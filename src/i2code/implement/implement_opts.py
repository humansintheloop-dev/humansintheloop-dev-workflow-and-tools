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

    def validate_trunk_options(self):
        """Raise click.UsageError if --trunk is combined with incompatible options."""
        incompatible = []
        if self.cleanup:
            incompatible.append("--cleanup")
        if self.setup_only:
            incompatible.append("--setup-only")
        if self.isolate:
            incompatible.append("--isolate")
        if self.isolated:
            incompatible.append("--isolated")
        if self.skip_ci_wait:
            incompatible.append("--skip-ci-wait")
        if self.ci_fix_retries != 3:
            incompatible.append("--ci-fix-retries")
        if self.ci_timeout != 600:
            incompatible.append("--ci-timeout")
        if incompatible:
            raise click.UsageError(
                f"--trunk cannot be combined with: {', '.join(incompatible)}"
            )
