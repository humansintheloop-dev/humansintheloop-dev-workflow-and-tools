#!/usr/bin/env bash
# Copies the idea, discussion and metadata fixture files (no spec) into the eval workspace.
set -euo pipefail

FIXTURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../fixtures/eval-idea" && pwd)"
IDEA_DIR="docs/ideas/active/eval-idea"

mkdir -p "$IDEA_DIR"
for file in eval-idea-idea.md eval-idea-discussion.md eval-idea-metadata.yaml; do
    cp "$FIXTURE_DIR/$file" "$IDEA_DIR/$file"
done
