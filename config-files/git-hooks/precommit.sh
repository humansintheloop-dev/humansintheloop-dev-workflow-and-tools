#!/bin/bash

set -e

# Directories to check - override for multi-repo projects with multiple subprojects
PRECOMMIT_DIRS="${PRECOMMIT_DIRS:-.}"

echo "Running pre-commit checks..."

# Function to check for uncommitted changes in a directory
has_uncommitted_changes() {
    local dir=$1
    cd "$dir"
    # Check for uncommitted changes (staged, unstaged, or untracked files)
    if git status --porcelain | grep -q "$dir"; then
        return 0  # Has changes
    else
        return 1  # No changes
    fi
}

# Get the root directory from the script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

cd # Process each directory
for dir in $PRECOMMIT_DIRS; do
       cd "$ROOT_DIR"
       if [ -d "$dir" ]; then
        echo ""
        echo "Checking $dir..."


        # Check for usage of org.junit.jupiter.api.Disabled in Java files
        if grep -r --include="*.java" "org\.junit\.jupiter\.api\.Disabled" "$dir"; then
            echo "Error: Found usage of org.junit.jupiter.api.Disabled in $dir. Please remove @Disabled annotations before committing."
            exit 1
        fi

        if has_uncommitted_changes "$dir"; then
            echo "Found uncommitted changes in $dir, running gradlew check..."
            cd "$ROOT_DIR/$dir"
            if [ "$dir" = "end-to-end-tests" ]; then
                # Skip end-to-end tests in pre-commit since they require Docker
                ./gradlew test
            else
                ./gradlew check
            fi
        else
            echo "No uncommitted changes in $dir, skipping checks"
        fi
    else
        echo "Directory $dir not found, skipping"
    fi
done

cd "$ROOT_DIR"
echo ""
echo "Pre-commit checks completed!"
