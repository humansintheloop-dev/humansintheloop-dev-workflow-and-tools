"""Implement configuration: read, write, prompt, and build flags for i2code implement."""

import os

INTERACTIVE = "Interactive"
NON_INTERACTIVE = "Non-interactive"
WORKTREE_MODE = "Worktree (branch + PR)"
TRUNK_MODE = "Trunk (current branch, no PR)"


def read_implement_config(path):
    """Read implement config from a YAML-like file.

    Returns a dict with 'interactive' and 'trunk' boolean keys,
    or None if the file does not exist.
    """
    if not os.path.isfile(path):
        return None

    values = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("interactive:"):
                values["interactive"] = line.split(":", 1)[1].strip() == "true"
            elif line.startswith("trunk:"):
                values["trunk"] = line.split(":", 1)[1].strip() == "true"

    if not values:
        return None

    values.setdefault("interactive", True)
    values.setdefault("trunk", False)
    return values


def write_implement_config(path, interactive, trunk):
    """Write implement config to a YAML-like file."""
    with open(path, "w") as f:
        f.write(f"interactive: {str(interactive).lower()}\n")
        f.write(f"trunk: {str(trunk).lower()}\n")


def prompt_implement_config(menu_fn):
    """Prompt the user for implement configuration using the provided menu function.

    Args:
        menu_fn: Callable(prompt, default, options) -> 1-based choice index.

    Returns:
        (interactive, trunk) boolean tuple.
    """
    mode_choice = menu_fn("How should Claude run?", 1, [INTERACTIVE, NON_INTERACTIVE])
    interactive = mode_choice == 1

    branch_choice = menu_fn(
        "Where should implementation happen?", 1,
        [WORKTREE_MODE, TRUNK_MODE],
    )
    trunk = branch_choice == 2

    return interactive, trunk


def build_implement_flags(config):
    """Build command-line flags from an implement config dict."""
    flags = []
    if not config["interactive"]:
        flags.append("--non-interactive")
    if config["trunk"]:
        flags.append("--trunk")
    return flags


def build_implement_label(config_path):
    """Build the menu label for the implement option.

    Shows the i2code implement command with flags when config exists.
    """
    config = read_implement_config(config_path)
    if config is not None:
        flags = build_implement_flags(config)
    else:
        flags = []

    suffix = " ".join(flags)
    if suffix:
        return f"Implement the entire plan: i2code implement {suffix}"
    return "Implement the entire plan: i2code implement"
