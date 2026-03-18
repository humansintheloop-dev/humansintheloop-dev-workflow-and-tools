"""Unit tests for ImplementOpts validation."""

from dataclasses import fields

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


@pytest.mark.unit
class TestInnerCliFlags:
    """inner_cli_flags() returns CLI args for flags passed to the inner i2code command."""

    def test_includes_bool_flag_when_set(self):
        opts = ImplementOpts(idea_directory="/tmp", cleanup=True)
        flags = opts.inner_cli_flags()
        assert "--cleanup" in flags

    def test_excludes_bool_flag_when_unset(self):
        opts = ImplementOpts(idea_directory="/tmp")
        flags = opts.inner_cli_flags()
        assert "--cleanup" not in flags

    def test_includes_value_flag_with_non_default_value(self):
        opts = ImplementOpts(idea_directory="/tmp", ci_fix_retries=5)
        flags = opts.inner_cli_flags()
        assert "--ci-fix-retries" in flags
        idx = flags.index("--ci-fix-retries")
        assert flags[idx + 1] == "5"

    def test_excludes_value_flag_with_default_value(self):
        opts = ImplementOpts(idea_directory="/tmp")
        flags = opts.inner_cli_flags()
        assert "--ci-fix-retries" not in flags

    def test_includes_address_review_comments(self):
        opts = ImplementOpts(idea_directory="/tmp", address_review_comments=True)
        flags = opts.inner_cli_flags()
        assert "--address-review-comments" in flags

    def test_returns_all_set_flags(self):
        opts = ImplementOpts(
            idea_directory="/tmp",
            cleanup=True,
            non_interactive=True,
            mock_claude="/mock.sh",
            extra_prompt="extra text",
            ci_fix_retries=5,
            ci_timeout=900,
        )
        flags = opts.inner_cli_flags()
        assert "--cleanup" in flags
        assert "--non-interactive" in flags
        assert "--mock-claude" in flags
        assert "/mock.sh" in flags
        assert "--extra-prompt" in flags
        assert "extra text" in flags
        assert "--ci-fix-retries" in flags
        assert "5" in flags
        assert "--ci-timeout" in flags
        assert "900" in flags


@pytest.mark.unit
class TestInnerFlagExhaustiveness:
    """Every dataclass field must be in _INNER_FORWARDED or _INNER_IGNORED."""

    def test_every_field_is_categorized(self):
        all_categorized = ImplementOpts._INNER_FORWARDED | ImplementOpts._INNER_IGNORED
        all_fields = {f.name for f in fields(ImplementOpts)}
        uncategorized = all_fields - all_categorized
        assert uncategorized == set(), (
            f"New field(s) {uncategorized} must be added to "
            f"_INNER_FORWARDED or _INNER_IGNORED"
        )

    def test_forwarded_and_ignored_are_disjoint(self):
        overlap = ImplementOpts._INNER_FORWARDED & ImplementOpts._INNER_IGNORED
        assert overlap == set(), (
            f"Field(s) {overlap} appear in both _INNER_FORWARDED and _INNER_IGNORED"
        )


@pytest.mark.unit
class TestValidateTrunkOptionsErrorMessage:

    def test_error_message_lists_all_incompatible_flags(self):
        opts = ImplementOpts(
            idea_directory="/tmp", trunk=True,
            cleanup=True, isolate=True,
        )
        with pytest.raises(click.UsageError, match="--cleanup.*--isolate"):
            opts.validate_trunk_options()
