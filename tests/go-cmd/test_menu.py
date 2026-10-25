"""Tests for go_cmd.menu — reusable numbered-option menu."""

import io

import pytest

from i2code.go_cmd.menu import MenuConfig, get_user_choice


def _config(input_fn, output=None):
    if output is None:
        output = io.StringIO()
    return MenuConfig(input_fn=input_fn, output=output)


class _TerminalOutput(io.StringIO):
    def isatty(self):
        return True


def _displayed_output(prompt, default, options, input_fn):
    buf = io.StringIO()
    get_user_choice(prompt, default, options, config=_config(input_fn, output=buf))
    return buf.getvalue()


def _displayed_on_terminal():
    terminal = _TerminalOutput()
    get_user_choice(
        "Pick one:", 2, ["Alpha", "Beta"],
        config=_config(lambda _: "2", output=terminal),
    )
    return terminal.getvalue()


@pytest.mark.unit
class TestGetUserChoiceValidInput:

    def test_returns_selected_option_index(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            config=_config(lambda _: "2"),
        )
        assert choice == 2

    def test_default_on_empty_input(self):
        choice = get_user_choice(
            "Pick one:", 2, ["Alpha", "Beta"],
            config=_config(lambda _: ""),
        )
        assert choice == 2

    def test_first_option_selectable(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta", "Gamma"],
            config=_config(lambda _: "1"),
        )
        assert choice == 1

    def test_last_option_selectable(self):
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta", "Gamma"],
            config=_config(lambda _: "3"),
        )
        assert choice == 3


@pytest.mark.unit
class TestGetUserChoiceDisplaysMenu:

    def test_displays_numbered_options_to_output(self):
        displayed = _displayed_output("Pick one:", 1, ["Alpha", "Beta"], lambda _: "1")
        assert "1) Alpha" in displayed
        assert "2) Beta" in displayed

    def test_marks_default_option(self):
        displayed = _displayed_output("Pick one:", 2, ["Alpha", "Beta"], lambda _: "2")
        assert "[default]" in displayed
        assert "2) Beta [default]" in displayed

    def test_bolds_default_option_on_terminal(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        displayed = _displayed_on_terminal()
        assert "\033[1m  2) Beta [default]\033[0m" in displayed
        assert "  1) Alpha\n" in displayed

    def test_does_not_bold_default_option_when_no_color_is_set(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        displayed = _displayed_on_terminal()
        assert "\033[" not in displayed
        assert "  2) Beta [default]\n" in displayed

    def test_displays_prompt(self):
        displayed = _displayed_output("Pick one:", 1, ["Alpha", "Beta"], lambda _: "1")
        assert "Pick one:" in displayed


@pytest.mark.unit
class TestGetUserChoiceInvalidInput:

    def test_retries_on_invalid_then_accepts_valid(self):
        inputs = iter(["0", "99", "abc", "2"])
        choice = get_user_choice(
            "Pick one:", 1, ["Alpha", "Beta"],
            config=_config(lambda _: next(inputs)),
        )
        assert choice == 2

    def test_invalid_input_shows_error_message(self):
        inputs = iter(["bad", "1"])
        displayed = _displayed_output(
            "Pick one:", 1, ["Alpha", "Beta"], lambda _: next(inputs),
        )
        assert "Invalid choice" in displayed


@pytest.mark.unit
class TestGetUserChoiceEOF:

    def test_eof_raises_system_exit_zero(self):
        def eof_input(_):
            raise EOFError()

        with pytest.raises(SystemExit) as exc_info:
            get_user_choice(
                "Pick one:", 1, ["Alpha", "Beta"],
                config=_config(eof_input),
            )
        assert exc_info.value.code == 0
