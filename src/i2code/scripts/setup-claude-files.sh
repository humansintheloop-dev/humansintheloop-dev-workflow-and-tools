#!/bin/bash -e

usage() {
    cat <<EOF
Usage: $(basename "$0") --config-dir CONFIG_DIR

Copy Claude configuration files into the current project directory.

Options:
  --config-dir DIR     Path to the config-files directory (required)
  --help               Show this help message and exit

Examples:
  $(basename "$0") --config-dir ~/workflow/config-files
EOF
}

CONFIG_DIR=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        --config-dir)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --config-dir requires a value" >&2
                exit 1
            fi
            CONFIG_DIR="$2"
            shift 2
            ;;
        *)
            echo "Error: Unrecognized argument: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$CONFIG_DIR" ]]; then
    echo "Error: --config-dir is required" >&2
    echo "Use --help for usage information" >&2
    exit 1
fi

cp "$CONFIG_DIR/CLAUDE.md" .
mkdir -p .claude
cp "$CONFIG_DIR/settings.local.json" .claude/
