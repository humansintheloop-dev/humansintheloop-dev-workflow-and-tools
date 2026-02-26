"""Tests for go_cmd.menu — reusable numbered-option menu."""

import io

import pytest

from i2code.go_cmd.menu import get_user_choice


@pytest.mark.unit
class TestGetUserChoiceValidInput:

    def test_returns_selected_option_index(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            input_fn=lambda _: "2",
            output=io.StringIO(),
        )
        assert choice == 2

    def test_default_on_empty_input(self):
        choice = get_user_choice(
            "Pick one:", 2, ["Alpha", "Beta"],
            input_fn=lambda _: "",
            output=io.StringIO(),
        )
        assert choice == 2

    def test_first_option_selectable(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta", "Gamma"],
            input_fn=lambda _: "1",
            output=io.StringIO(),
        )
        assert choice == 1

    def test_last_option_selectable(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta", "Gamma"],
            input_fn=lambda _: "3",
            output=io.StringIO(),
        )
        assert choice == 3


@pytest.mark.unit
class TestGetUserChoiceDisplaysMenu:

    def test_displays_numbered_options_to_output(self):
        buf = io.StringIO()
        get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            input_fn=lambda _: "1",
            output=buf,
        )
        displayed = buf.getvalue()
        assert "1) Alpha" in displayed
        assert "2) Beta" in displayed

    def test_marks_default_option(self):
        buf = io.StringIO()
        get_user_choice(
            "Pick one:", 2, ["Alpha", "Beta"],
            input_fn=lambda _: "2",
            output=buf,
        )
        displayed = buf.getvalue()
        assert "[default]" in displayed
        assert "2) Beta [default]" in displayed

    def test_displays_prompt(self):
        buf = io.StringIO()
        get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            input_fn=lambda _: "1",
            output=buf,
        )
        displayed = buf.getvalue()
        assert "Pick one:" in displayed


@pytest.mark.unit
class TestGetUserChoiceInvalidInput:

    def test_retries_on_invalid_then_accepts_valid(self):
        inputs = iter(["0", "99", "abc", "2"])
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            input_fn=lambda _: next(inputs),
            output=io.StringIO(),
        )
        assert choice == 2

    def test_invalid_input_shows_error_message(self):
        inputs = iter(["bad", "1"])
        buf = io.StringIO()
        get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            input_fn=lambda _: next(inputs),
            output=buf,
        )
        displayed = buf.getvalue()
        assert "Invalid choice" in displayed


@pytest.mark.unit
class TestGetUserChoiceEOF:

    def test_eof_raises_system_exit_zero(self):
        def eof_input(_):
            raise EOFError()

        with pytest.raises(SystemExit) as exc_info:
            get_user_choice(
                "Pick one:", 1, ["Alpha", "Beta"],
                input_fn=eof_input,
                output=io.StringIO(),
            )
        assert exc_info.value.code == 0
