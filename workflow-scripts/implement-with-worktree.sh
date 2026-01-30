#!/usr/bin/env bash
# Entry point for implement-with-worktree workflow
# Sources Python helper and delegates to Python implementation

set -e

# shellcheck source=_python_helper.sh
source "$(dirname "$0")/_python_helper.sh"

run_python "$(dirname "$0")/implement_with_worktree.py" "$@"
