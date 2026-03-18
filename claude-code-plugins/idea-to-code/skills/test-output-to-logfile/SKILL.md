---
name: test-output-to-logfile
description: When running test scripts or long-running commands that produce verbose output, redirect output to a log file under logs/ to avoid truncation in the Bash tool. Claude should use this skill when running test scripts, end-to-end tests, or any command likely to produce large output.
---

# Redirect verbose command output to log files

When running test scripts or any command that may produce large output (e.g. end-to-end tests, integration tests, build scripts):

1. Ensure a `logs/` directory exists in the project root
2. Ensure `logs/` is in `.gitignore`
3. Redirect both stdout and stderr to a file under `logs/`, e.g.:
   ```
   ./test-scripts/test-end-to-end.sh > logs/e2e.log 2>&1
   ```
4. Check the exit code, then read the relevant parts of the log file using the Read tool
5. If the command failed, read the tail of the log file to find the error

This prevents the Bash tool from truncating output and losing important error details.
