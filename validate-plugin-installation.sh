#!/bin/bash -e

# Validate that the idea-to-code plugin is properly installed
# by running Claude and asking it to verify the plugin, skills, and slash commands

newest_file_in() {
    local newest=""
    local file
    for file in "$1"/*; do
        if [ -z "$newest" ] || [ "$file" -nt "$newest" ]; then
            newest="$file"
        fi
    done
    echo "$newest"
}

echo "Validating plugin installation..."
echo

claude -p "hello"

grep idea-to-code "$(newest_file_in "$HOME/.claude/debug")"
