"""Unit tests for ImplementOpts validation."""

import click
import pytest

from i2code.implement.implement_opts import ImplementOpts


@pytest.mark.unit
class TestValidateTrunkOptions:
    """validate_trunk_options() rejects flags incompatible with --trunk."""

    @pytest.mark.parametrize("kwarg", [
        "cleanup",
        "setup_only",
        "isolate",
        "isolated",
        "skip_ci_wait",
    ])
    def test_boolean_flag_raises_usage_error(self, kwarg):
        opts = ImplementOpts(idea_directory="/tmp", trunk=True, **{kwarg: True})
        with pytest.raises(click.UsageError, match="cannot be combined"):
            opts.validate_trunk_options()

    @pytest.mark.parametrize("kwarg,value", [
        ("ci_fix_retries", 5),
        ("ci_timeout", 900),
    ])
    def test_non_default_ci_option_raises_usage_error(self, kwarg, value):
        opts = ImplementOpts(idea_directory="/tmp", trunk=True, **{kwarg: value})
        with pytest.raises(click.UsageError, match="cannot be combined"):
            opts.validate_trunk_options()

    def test_defaults_pass_validation(self):
        opts = ImplementOpts(idea_directory="/tmp", trunk=True)
        opts.validate_trunk_options()  # should not raise

    def test_address_review_comments_raises_usage_error(self):
        opts = ImplementOpts(
            idea_directory="/tmp", trunk=True,
            address_review_comments=True,
        )
        with pytest.raises(click.UsageError, match="cannot be combined"):
            opts.validate_trunk_options()

    def test_address_review_comments_without_trunk_passes(self):
        opts = ImplementOpts(
            idea_directory="/tmp",
            address_review_comments=True,
        )
        opts.validate_trunk_options()  # should not raise

    def test_error_message_lists_all_incompatible_flags(self):
        opts = ImplementOpts(
            idea_directory="/tmp", trunk=True,
            cleanup=True, isolate=True,
        )
        with pytest.raises(click.UsageError, match="--cleanup.*--isolate"):
            opts.validate_trunk_options()
