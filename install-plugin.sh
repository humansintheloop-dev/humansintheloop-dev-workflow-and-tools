#!/bin/bash -e

claude plugin marketplace add ./ 2>/dev/null || echo marketplace already installed  

claude plugin uninstall idea-to-code@idea-to-code-marketplace || echo plugin not installed
claude plugin install idea-to-code@idea-to-code-marketplace