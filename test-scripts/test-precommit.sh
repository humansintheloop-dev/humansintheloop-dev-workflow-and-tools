#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

unset GIT_INDEX_FILE
unset GIT_DIR
unset GIT_WORK_TREE

echo NOT running integratino_gh tests

export CI=yes

./test-scripts/test-end-to-end.sh

echo "Pre-commit checks completed!"