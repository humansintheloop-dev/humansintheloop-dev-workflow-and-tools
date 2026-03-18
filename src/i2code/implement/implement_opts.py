"""Options dataclass for the implement command."""

from dataclasses import dataclass, fields

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
    shell: bool = False
    trunk: bool = False
    dry_run: bool = False
    ignore_uncommitted_idea_changes: bool = False
    address_review_comments: bool = False
    skip_scaffolding: bool = False
    debug_claude: bool = False

    _INNER_FORWARDED = {
        "cleanup",
        "setup_only",
        "non_interactive",
        "skip_ci_wait",
        "debug_claude",
        "address_review_comments",
        "mock_claude",
        "extra_prompt",
        "ci_fix_retries",
        "ci_timeout",
    }

    _INNER_IGNORED = {
        "idea_directory",
        "isolate",
        "isolation_type",
        "isolated",
        "shell",
        "trunk",
        "dry_run",
        "ignore_uncommitted_idea_changes",
        "skip_scaffolding",
    }

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

    def inner_cli_flags(self):
        """Return CLI flags to pass to the inner i2code implement command."""
        result = []
        for f in fields(self):
            if f.name not in self._INNER_FORWARDED:
                continue
            value = getattr(self, f.name)
            if value == f.default:
                continue
            flag = "--" + f.name.replace("_", "-")
            if f.type is bool:
                result.append(flag)
            else:
                result.extend([flag, str(value)])
        return result
