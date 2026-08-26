---
name: test-output-to-logfile
description: When running test scripts or long-running commands that produce verbose output, redirect output to a log file under logs/ to avoid truncation in the Bash tool. Claude should use this skill when running test scripts, end-to-end tests, or any command likely to produce large output, and also when waiting for a background command to finish — it covers how to block on the command without polling the log or ending the turn. NOTE: This skill does not apply to Gradle because test output is written to TEST*.xml files.
---

# Redirect verbose command output to log files

When running test scripts or any command that may produce large output (e.g. end-to-end tests, integration tests, build scripts):

## Setup

1. Ensure a `logs/` directory exists in the project root
2. Ensure log files are covered by `.gitignore` (either `logs/` or `*.log`)
3. Check whether the script already writes its own log. Many do. If it prints a banner naming the file (e.g. `=== Logging to logs/test-ec2-20260821-111338.log ===`), use that file and skip the redirect.

## Running the command

4. Redirect both stdout and stderr to a file under `logs/`, and run in the background:
   ```
   ./build-and-test-all.sh > logs/build-and-test.log 2>&1
   ```
   Use `run_in_background: true` on the Bash tool so you are free to do other work while it runs.

5. **Use a literal path as the redirect target.** `> $LOGDIR/build.log` is rejected by the Bash permission checker as an unanalyzable substitution; `> logs/build-and-test.log` is accepted.

   A literal redirect does not make the whole command allowed. The rest of it still has to match an allow rule — a flag the rules do not cover is denied whether or not output is redirected. If that happens, say so and ask for the permission. Do not fall back to running it in the foreground and dumping the output into context.

6. **Keep commands simple.** Avoid compound commands with `&&`, quoted flag characters, or other complexity that may be rejected by the Bash tool permission system. Run each command as a separate Bash call.

## Waiting for completion

7. **Usually you do not need a waiter.** A command started with `run_in_background: true` notifies you exactly once when it exits, and the notification carries the real exit code (see step 13). That is a better signal than any log grep, because it reads process status instead of guessing from text.

   **Waiting means keeping the turn open.** The notification only arrives while the session is alive. In an autonomous session (i2code driving Claude) the end of your turn is the end of the process, and a background command still running is killed with it — no notification, no result, and a test run that has to be repeated from scratch. Never end the turn with "waiting on the suite"; it is not waiting, it is abandoning the run. If you have nothing else to do while the command runs, block on it:
   ```
   TaskOutput(task_id=<id>, block=true, timeout=600000)
   ```
   and re-issue it until the task reports that it has exited. With the output redirected to a log file this returns next to nothing, so it does not dump the run into context. End the turn only when the command has exited and you have read its result.

   `TaskOutput` is marked deprecated in its tool description (which steers you towards reading the task's output file). Use it anyway: it is the only tool that blocks the turn on a background task, and the deprecation is about *reading* output, not about waiting. Do not let the deprecation notice push you back to polling.

8. **Do not poll the log with repeated `tail` calls.** Polling burns a tool call per check, and a quiet log is indistinguishable from a finished one — so it tends to either spam checks or overshoot the finish by minutes.

9. **Write a waiter only when process exit is not the signal you want** — an intermediate milestone while the process keeps running, or a log written by a process this session did not start:
   ```
   until grep -q "Listening on" logs/dev-server.log; do sleep 5; done
   ```
   Run it with `run_in_background: true`. The `sleep` must be inside a backgrounded command — a foreground `sleep` is blocked.

10. **A completion waiter must match completion, not failure.** Wait on the marker the runner prints once, at the very end (e.g. `=== All tests passed ===`):
    ```
    until grep -q "=== All tests passed ===" logs/build-and-test.log; do sleep 10; done
    ```
    Do not put `^FAIL`, `panic:`, or `Error:` in a completion waiter. They appear mid-run, per package, while other packages are still going, and `Error:` is routinely the expected output of a passing negative test — a waiter matching them fires early on suites that go on to pass.

    Early warning of breakage is a separate job. Use the Monitor tool with a failure-signature filter for that, and keep it distinct from the waiter:
    ```
    Monitor(command='tail -f logs/build-and-test.log | grep -E --line-buffered "^FAIL|panic:|Traceback"',
            description='failures in build-and-test.log', timeout_ms=1800000, persistent=false)
    ```
    `grep` needs `--line-buffered` or matches sit in its buffer unseen. The default `timeout_ms` is 5 minutes, so set it longer than the run. `tail -f` never exits on its own, so `TaskStop` the monitor once the run's exit notification arrives.

11. **Never use `tail -f logs/build.log | grep -m1 ...` to wait.** It looks like it exits on the match, but it does not: `grep` exits, and `tail -f` only dies on SIGPIPE from its *next* write. If the log goes quiet after the match — which is exactly what happens when a test run finishes — nothing is ever written again, so the pipeline hangs until the Bash tool's timeout (2 minutes by default, 10 minutes at most). This has cost entire multi-minute waits on runs that had already passed.

12. When Docker containers are involved, check their health in parallel:
    ```
    docker ps --format "table {{.Names}}\t{{.Status}}"
    ```

## After completion

13. Check the exit code from the background task notification.

14. **Read the log, not the whole output.** The point of redirecting was to keep the output out of context. Do not undo that by reading the result through `TaskOutput`, which returns whatever the task wrote to stdout (blocking on it to keep the turn open, step 7, is fine; reading a non-redirected run's output through it is not). Use `Grep` or `tail` on the log file instead:
    ```
    Grep with pattern="FAILED|error|Exception" path="logs/build-and-test.log" output_mode="content"
    ```
    On success the terminal banner is usually all you need:
    ```
    tail -5 logs/build-and-test.log
    ```

15. For Gradle/JUnit failures, read the `TEST-*.xml` files rather than parsing log output — they contain full stack traces

This prevents the Bash tool from truncating output and losing important error details.
