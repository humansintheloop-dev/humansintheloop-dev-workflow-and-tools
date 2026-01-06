#!/bin/bash -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONFIG_DIR="$DIR/../config-files"

cp "$CONFIG_DIR/CLAUDE.md" .
mkdir -p .claude
cp "$CONFIG_DIR/settings.local.json" .claude/
