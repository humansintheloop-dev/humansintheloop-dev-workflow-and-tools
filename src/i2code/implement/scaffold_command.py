"""ScaffoldCommand encapsulates the scaffold workflow logic."""


class ScaffoldCommand:
    """Generates project scaffolding for an idea directory."""

    def __init__(self, opts, initializer, cwd):
        self.opts = opts
        self.initializer = initializer
        self.cwd = cwd

    def execute(self):
        """Run scaffolding with the configured initializer."""
        self.initializer.run_scaffolding(
            self.opts.idea_directory,
            cwd=self.cwd,
            interactive=self.opts.interactive,
            mock_claude=self.opts.mock_claude,
        )
