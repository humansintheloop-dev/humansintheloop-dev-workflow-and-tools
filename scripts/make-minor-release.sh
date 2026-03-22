#!/usr/bin/env bash
set -euo pipefail

ECHO=""
if [ "${1:-}" = "--dry-run" ]; then
  ECHO="echo"
fi

if [ -z "${CI:-}" ]; then
  current_branch=$(git branch --show-current)
  if [ "$current_branch" != "master" ]; then
    echo "ERROR: Must be on master branch (currently on $current_branch)" >&2
    exit 1
  else
    echo "On master branch"
  fi

  local_sha=$(git rev-parse HEAD)
  remote_sha=$(git ls-remote origin refs/heads/master | cut -f1)
  if [ "$local_sha" != "$remote_sha" ]; then
    echo "ERROR: Local master ($local_sha) differs from origin/master ($remote_sha)" >&2
    exit 1
  else
    echo "Local and remote in sync"
  fi

  main_sha=$remote_sha
  conclusion=$(gh run list --commit "$main_sha" --workflow CI --json conclusion --jq '.[0].conclusion')
  if [ "$conclusion" != "success" ]; then
    echo "ERROR: CI workflow on master HEAD ($main_sha) did not pass (status: ${conclusion:-unknown})" >&2
    exit 1
  else
    echo "CI passed"
  fi
fi

latest_tag=$(git tag --list 'v*.*.*' --sort=-version:refname | head -n1)
if [ -z "$latest_tag" ]; then
  latest_tag="v0.0.0"
fi

version="${latest_tag#v}"
IFS='.' read -r major minor _ <<< "$version"
minor=$((minor + 1))
next_tag="v${major}.${minor}.0"

echo "Latest tag: $latest_tag"
echo "Next tag:   $next_tag"

$ECHO git tag "$next_tag"
$ECHO git push origin "$next_tag"
