#!/bin/bash -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_JSON="$SCRIPT_DIR/claude-code-plugins/idea-to-code/.claude-plugin/plugin.json"
TIMESTAMP=$(date +"%Y%m%d%H%M%S")

if [ "$1" = "--force" ]; then
  echo "timestamp version is $TIMESTAMP"
  sed -i '' "s/\"version\": \"1.0.[^\"]*\"/\"version\": \"1.0.$TIMESTAMP\"/" "$PLUGIN_JSON"
  #trap 'sed -i "" "s/\"version\": \"1.0.$TIMESTAMP\"/\"version\": \"1.0.0\"/" "$PLUGIN_JSON"' EXIT
fi

claude plugin marketplace add "$SCRIPT_DIR" 2>/dev/null || echo marketplace already installed

claude plugin uninstall idea-to-code@idea-to-code-marketplace || echo plugin not installed

claude plugin install idea-to-code@idea-to-code-marketplace