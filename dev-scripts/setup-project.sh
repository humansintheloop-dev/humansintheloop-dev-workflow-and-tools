#! /bin/bash -e

pre-commit install

if command -v setup-codescene-mcp.sh > /dev/null 2>&1; then
    setup-codescene-mcp.sh
else
    echo setup-codescene-mcp.sh NOT FOUND
fi

