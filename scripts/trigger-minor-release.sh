#!/usr/bin/env bash
set -euo pipefail

args=()
if [ "${1:-}" = "--dry-run" ]; then
  args+=(-f dry-run=true)
fi

gh workflow run make-minor-release.yml "${args[@]}"
echo "Triggered make-minor-release workflow"
echo "Watch with: gh run watch"
