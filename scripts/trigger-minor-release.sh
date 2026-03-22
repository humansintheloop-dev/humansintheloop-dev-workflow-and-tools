#!/usr/bin/env bash
set -euo pipefail

args=(-f release=true)
if [ -n "${1:-}" ]; then
  args+=(-f "version=$1")
fi

gh workflow run ci.yml "${args[@]}"
echo "Triggered CI workflow with release"
echo "Watch with: gh run watch"
