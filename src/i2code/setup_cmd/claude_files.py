"""Copy Claude configuration files into a project directory."""

import os
import shutil
import sys


def setup_claude_files(config_dir, *, target_dir="."):
    """Copy CLAUDE.md and settings.local.json from config_dir into target_dir.

    Copies CLAUDE.md to target_dir and settings.local.json to target_dir/.claude/.
    Creates .claude/ if it does not exist.
    """
    if not os.path.isdir(config_dir):
        print(f"Error: config directory does not exist: {config_dir}", file=sys.stderr)
        raise SystemExit(1)

    claude_md = os.path.join(config_dir, "CLAUDE.md")
    if not os.path.isfile(claude_md):
        print(f"Error: CLAUDE.md not found in {config_dir}", file=sys.stderr)
        raise SystemExit(1)

    settings_file = os.path.join(config_dir, "settings.local.json")
    if not os.path.isfile(settings_file):
        print(f"Error: settings.local.json not found in {config_dir}", file=sys.stderr)
        raise SystemExit(1)

    shutil.copy2(claude_md, target_dir)

    claude_dir = os.path.join(target_dir, ".claude")
    os.makedirs(claude_dir, exist_ok=True)

    shutil.copy2(settings_file, claude_dir)
