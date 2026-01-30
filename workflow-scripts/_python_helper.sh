# shellcheck disable=SC2148
# Shared Python venv bootstrap logic for workflow scripts
# Source this file in bash scripts that need to call Python

# Get the directory where the helper script resides
_PYTHON_HELPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensures the Python virtual environment exists and has dependencies installed
# Creates .venv in the workflow-scripts directory if it doesn't exist
ensure_venv() {
    local venv_dir="$_PYTHON_HELPER_DIR/.venv"
    local requirements_file="$_PYTHON_HELPER_DIR/requirements.txt"

    if [ ! -d "$venv_dir" ]; then
        echo "Creating Python virtual environment..." >&2
        python3 -m venv "$venv_dir"
    fi

    if [ -f "$requirements_file" ]; then
        # Install/update dependencies
        "$venv_dir/bin/pip" install -q -r "$requirements_file"
    fi
}

# Ensures venv exists, then runs a Python script with arguments
# Usage: run_python script.py [args...]
run_python() {
    ensure_venv
    "$_PYTHON_HELPER_DIR/.venv/bin/python" "$@"
}
