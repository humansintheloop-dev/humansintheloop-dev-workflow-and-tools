"""ClaudeServices: bundles claude_runner and command_builder."""

from dataclasses import dataclass


@dataclass
class ClaudeServices:
    """A claude runner and the command builder it uses."""

    claude_runner: object
    command_builder: object
