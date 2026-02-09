#!/bin/bash -e

claude plugin uninstall idea-to-code@idea-to-code-marketplace || echo plugin not installed
claude plugin marketplace remove idea-to-code-marketplace || echo marketplace not installed
