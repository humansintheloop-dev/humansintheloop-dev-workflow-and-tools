#!/bin/bash -e

PLUGIN_JSON=".claude-plugin/plugin.json"
TIMESTAMP=$(date +"%Y%m%d%H%M%S")

if [ "$1" = "--force" ]; then
  echo timestamp version is $TIMESTAMP
  sed -i '' "s/\"version\": \"1.0.[^\"]*\"/\"version\": \"1.0.$TIMESTAMP\"/" "$PLUGIN_JSON"
  #trap 'sed -i "" "s/\"version\": \"1.0.$TIMESTAMP\"/\"version\": \"1.0.0\"/" "$PLUGIN_JSON"' EXIT
fi

claude plugin marketplace add ./ 2>/dev/null || echo marketplace already installed

claude plugin uninstall idea-to-code@idea-to-code-marketplace || echo plugin not installed

claude plugin install idea-to-code@idea-to-code-marketplace