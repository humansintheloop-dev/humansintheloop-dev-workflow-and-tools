---
name: test-output-to-logfile
description: When running test scripts or long-running commands that produce verbose output, redirect output to a log file under logs/ to avoid truncation in the Bash tool. Claude should use this skill when running test scripts, end-to-end tests, or any command likely to produce large output.
---

# Redirect verbose command output to log files

When running test scripts or any command that may produce large output (e.g. end-to-end tests, integration tests, build scripts):

## Setup

1. Ensure a `logs/` directory exists in the project root
2. Ensure log files are covered by `.gitignore` (either `logs/` or `*.log`)

## Running the command

3. Redirect both stdout and stderr to a file under `logs/`, and run in the background:
   ```
   ./build-and-test-all.sh > logs/build-and-test.log 2>&1
   ```
   Use `run_in_background: true` on the Bash tool so you can monitor progress immediately rather than waiting for completion.

4. **Keep commands simple.** Avoid compound commands with `&&`, quoted flag characters, or other complexity that may be rejected by the Bash tool permission system. Run each command as a separate Bash call.

## Monitoring

5. **Actively monitor** the log file while the command runs — don't just wait for completion:
   ```
   tail -30 logs/build-and-test.log
   ```
6. When Docker containers are involved, check their health in parallel:
   ```
   docker ps --format "table {{.Names}}\t{{.Status}}"
   ```
7. Diagnose issues as soon as they appear in the log. Don't wait for the command to finish if you can see it's already failing.

## After completion

8. Check the exit code from the background task notification
9. If the command failed, use `tail` or `Grep` on the log file to find the error:
   ```
   Grep with pattern="FAILED|error|Exception" path="logs/build-and-test.log" output_mode="content"
   ```
10. For Gradle/JUnit failures, read the `TEST-*.xml` files rather than parsing log output — they contain full stack traces

This prevents the Bash tool from truncating output and losing important error details.
