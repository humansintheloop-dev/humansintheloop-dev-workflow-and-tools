---
name: debugging-ci-failures
description: Guidelines for watching CI builds and diagnosing failures. Claude should use this skill when watching a CI build or investigating why a CI build failed.
---

# Watching and Debugging CI Builds

This skill covers two scenarios: watching a CI build to completion after a push, and diagnosing failures when a build fails. Start with Phase 0 to monitor the build. If it succeeds, you're done. If it fails, continue to Phase 1 to gather evidence and Phase 2 to analyze and fix.

## Phase 0: Watch a Running Build

When asked to watch a CI build after a push, actively poll until the build completes.

### Detect CI system

Check which CI system the project uses:
- `.github/workflows/*.yml` → GitHub Actions
- `.circleci/config.yml` → CircleCI

For CircleCI, extract the org and repo from `git remote get-url origin` to construct API URLs.

### GitHub Actions: Watch a build

Poll using the `gh` CLI (no caching issues):
```bash
gh run list --branch <branch> --limit 1 --json status,conclusion,databaseId,name
```

Then poll the specific run until it completes:
```bash
gh run view <run-id> --json status,conclusion,jobs
```

Repeat every 10-15 seconds until `status` is `completed`. Then check `conclusion` for `success` or `failure`.

### CircleCI: Watch a build

**IMPORTANT:** The WebFetch tool has a 15-minute cache. To get fresh data on each poll, append a unique query parameter (e.g., `&_ts=1`, `&_ts=2`, incrementing each time).

1. Find the latest build:
```
WebFetch: https://circleci.com/api/v1.1/project/github/<org>/<repo>?limit=1&branch=<branch>&_ts=1
```
Extract the `build_num`.

2. Poll the build status, incrementing `_ts` each time:
```
WebFetch: https://circleci.com/api/v1.1/project/github/<org>/<repo>/<build-num>?_ts=<N>
```
Ask for the `status`, `outcome`, and `stop_time` fields.

3. Repeat every 10-15 seconds until `status` is no longer `running`.

4. Report the final result: `success` or `failed`.

If the build failed, proceed to Phase 1 below.

## Phase 1: Gather Evidence (only if the build failed)

Collect all available information before drawing any conclusions.

### Step 1: Get the failed job summary

**GitHub Actions:**
```bash
gh run view <run-id> --log-failed 2>&1 | grep -i "FAILED\|error\|Exception" | head -30
```

This gives you the failing task/test name and a high-level error.

**CircleCI:**
First get the build steps:
```
WebFetch: https://circleci.com/api/v1.1/project/github/<org>/<repo>/<build-num>?include=steps
```
Then fetch the output for the failed step index:
```
WebFetch: https://circleci.com/api/v1.1/project/github/<org>/<repo>/<build-num>/output/<step-index>/0
```

### Step 2: Download test artifacts

Check the workflow definition for uploaded artifacts.

**GitHub Actions:**
Test results are often saved via `actions/upload-artifact`. If artifacts are available:

```bash
gh run download <run-id> --name <artifact-name> --dir test-reports
```

**CircleCI:**
List artifacts:
```
WebFetch: https://circleci.com/api/v1.1/project/github/<org>/<repo>/<build-num>/artifacts
```
Then fetch specific artifact URLs from the response.

### Step 3: Read the TEST-*.xml files

Find and read the relevant `TEST-*.xml` file for the failing test. These files contain:
- The full stack trace (not truncated like CI logs)
- Container/service logs (stdout/stderr captured during the test)
- The actual root cause error, not just the symptom

Testcontainers-based tests typically configure `.withLogConsumer(new Slf4jLogConsumer(logger).withPrefix("SVC <service-name>"))`, so container logs appear in the XML prefixed with `[SVC <service-name>]`. Use this prefix to filter for the specific container's output when searching for errors.

Use the `Glob` tool to find the relevant test result:

```
Glob with pattern="**/TEST-*FailingTestName*.xml" path="test-reports"
```

Use the `Grep` tool to search within large XML files for the root cause:

```
Grep with pattern="ERROR|Exception|FATAL|Application run failed" path="test-reports/path/to/TEST-*.xml" output_mode="content"
```

**Do NOT read HTML reports** — they are for humans in browsers. The XML files contain the same information in a machine-readable format.

**Do NOT download artifacts to `/tmp`** or other directories outside the sandbox — download to a project-relative path like `test-reports/`.

## Phase 2: Analyze Evidence and Determine Problem

Only after gathering evidence, analyze it systematically.

### Step 1: Identify the root cause error

Look past the test framework wrappers. A typical failure chain looks like:

```
TestName > testMethod() FAILED
  IllegalStateException          ← symptom (Spring context failed)
    CompletionException          ← symptom (async wrapper)
      ContainerLaunchException   ← symptom (container didn't start)
        THE ACTUAL ERROR         ← root cause (e.g., missing bean, bad config, JDK bug)
```

Read the full chain — the root cause is at the bottom.

### Step 2: Determine if the failure is related to your changes

- Check if the failing test was actually passing before by examining the previous successful run
- A test marked `FROM-CACHE` in a previous run means it wasn't re-executed then — it may have been broken already
- Don't assume your changes caused the failure just because they were in the same commit

### Step 3: Fix the root cause, not the symptom

- If a container crashes on startup, read the container logs in the XML to find out why
- If a Spring context fails to load, find the specific bean creation error
- If a test times out, determine what it was waiting for

## Common Mistakes to Avoid

- **Don't skip evidence gathering**: Never propose a fix based on the one-line CI summary alone
- **Don't assume based on recent changes**: Just because you recently modified something doesn't mean it's the cause
- **Don't confuse file types**: A `FileNotFoundException` for a `.yml` file is different from a missing `.class` file
- **Don't implement fixes without understanding**: If you can't explain exactly why the fix works, you don't understand the problem
- **Don't search JAR files or external libraries** when the error is in your project code
- **Don't launch research agents** when a targeted `grep` or `read` of the test XML will give you the answer
- **CircleCI orb parameters**: When a build fails due to wrong JVM/tool version, check the orb's parameters (e.g., `java_version_to_install`, `machine_image`). Compare with other upgraded projects that use the same orb.

## Verification Steps

1. After implementing a fix, run the same command that failed in CI
2. Verify the specific test or task that failed now passes
3. If CI fails again with the same error, your fix was wrong — go back to Phase 1

## Pattern-Based Problems

When fixing issues caused by naming conventions or patterns:
1. Search the entire codebase for similar occurrences before making any changes
2. Fix ALL instances in a single commit
3. Never commit partial fixes for pattern-based problems
