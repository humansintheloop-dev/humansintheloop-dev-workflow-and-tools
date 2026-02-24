"""Options dataclass for the scaffold command."""

from dataclasses import dataclass


@dataclass
class ScaffoldOpts:
    """All options for the scaffold command."""

    idea_directory: str
    non_interactive: bool = False
    mock_claude: str | None = None

    @property
    def interactive(self):
        return not self.non_interactive
