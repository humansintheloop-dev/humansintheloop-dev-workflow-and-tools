"""ClaudeServices: bundles claude_runner and command_builder."""

from dataclasses import dataclass

from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.command_builder import CommandBuilder


@dataclass
class ClaudeServices:
    """A claude runner and the command builder it uses."""

    claude_runner: ClaudeRunner
    command_builder: CommandBuilder
