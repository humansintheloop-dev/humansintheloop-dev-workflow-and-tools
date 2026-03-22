#!/usr/bin/env bash
set -euo pipefail

# Outputs the next minor version tag based on the latest existing tag.

latest_tag=$(git tag --list 'v*.*.*' --sort=-version:refname | head -n1)
if [ -z "$latest_tag" ]; then
  latest_tag="v0.0.0"
fi

version="${latest_tag#v}"
IFS='.' read -r major minor _ <<< "$version"
minor=$((minor + 1))

echo "v${major}.${minor}.0"
