"""Reusable numbered-option menu for interactive workflows."""

import sys


def get_user_choice(prompt, default, options, *, input_fn=input, output=sys.stderr):
    """Display numbered options and return the user's selection.

    Args:
        prompt: Header text displayed above the options.
        default: 1-based index of the default option.
        options: List of option label strings.
        input_fn: Callable for reading user input (injectable for testing).
        output: Writable stream for menu display (defaults to stderr).

    Returns:
        1-based index of the selected option.

    Raises:
        SystemExit(0): On EOF (e.g. piped input closed).
    """
    print("", file=output)
    print(prompt, file=output)
    for i, option in enumerate(options):
        label = f"  {i + 1}) {option}"
        if i + 1 == default:
            label += " [default]"
        print(label, file=output)
    print("", file=output)

    prompt_text = f"Enter your choice (1-{len(options)})"
    if default:
        prompt_text += f" [default: {default}]"
    prompt_text += ": "

    while True:
        try:
            choice = input_fn(prompt_text)
        except EOFError:
            print("", file=output)
            print("Input closed. Exiting.", file=output)
            sys.exit(0)

        if choice == "" and default:
            return default

        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return int(choice)

        print(
            f"Invalid choice. Please enter a number between 1 and {len(options)}.",
            file=output,
        )
