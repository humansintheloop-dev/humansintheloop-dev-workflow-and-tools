"""Reusable numbered-option menu for interactive workflows."""

import sys
from dataclasses import dataclass, field
from typing import Callable, TextIO


@dataclass
class MenuConfig:
    """I/O configuration for menu display and input."""

    input_fn: Callable[[str], str] = field(default_factory=lambda: input)
    output: TextIO = field(default_factory=lambda: sys.stderr)


def _display_options(prompt, options, default, output):
    print("", file=output)
    print(prompt, file=output)
    for i, option in enumerate(options):
        label = f"  {i + 1}) {option}"
        if i + 1 == default:
            label += " [default]"
        print(label, file=output)
    print("", file=output)


def _build_prompt_text(option_count, default):
    prompt_text = f"Enter your choice (1-{option_count})"
    if default:
        prompt_text += f" [default: {default}]"
    prompt_text += ": "
    return prompt_text


def _read_choice(prompt_text, config):
    try:
        return config.input_fn(prompt_text)
    except EOFError:
        print("", file=config.output)
        print("Input closed. Exiting.", file=config.output)
        sys.exit(0)


def _parse_choice(raw_input, option_count, default):
    if raw_input == "" and default:
        return default
    if raw_input.isdigit() and 1 <= int(raw_input) <= option_count:
        return int(raw_input)
    return None


def get_user_choice(prompt, default, options, *, config=None):
    """Display numbered options and return the user's selection.

    Args:
        prompt: Header text displayed above the options.
        default: 1-based index of the default option.
        options: List of option label strings.
        config: MenuConfig with input_fn and output stream (defaults apply).

    Returns:
        1-based index of the selected option.

    Raises:
        SystemExit(0): On EOF (e.g. piped input closed).
    """
    if config is None:
        config = MenuConfig()

    _display_options(prompt, options, default, config.output)
    prompt_text = _build_prompt_text(len(options), default)

    while True:
        choice = _read_choice(prompt_text, config)
        parsed = _parse_choice(choice, len(options), default)
        if parsed is not None:
            return parsed
        print(
            f"Invalid choice. Please enter a number between 1 and {len(options)}.",
            file=config.output,
        )
