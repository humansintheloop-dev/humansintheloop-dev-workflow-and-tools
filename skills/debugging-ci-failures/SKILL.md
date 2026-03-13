---
name: debugging-ci-failures
description: Guidelines for diagnosing and fixing CI build failures. Claude should use this skill when investigating why a CI build failed.
---

# Debugging CI Build Failures

When a CI build fails, follow a two-phase approach: gather evidence first, then analyze.

## Phase 1: Gather Evidence

Collect all available information before drawing any conclusions.

### Step 1: Identify the failed run

```bash
gh run list --branch <branch> --limit 5
```

### Step 2: Get the failed job summary

```bash
gh run view <run-id> --log-failed 2>&1 | grep -i "FAILED\|error\|Exception" | head -30
```

This gives you the failing task/test name and a high-level error.

### Step 3: Download test artifacts

Check the workflow definition (`.github/workflows/*.yml`) for uploaded artifacts — test results are often saved via `actions/upload-artifact`. If artifacts are available:

```bash
gh run download <run-id> --name <artifact-name> --dir test-reports
```

### Step 4: Read the TEST-*.xml files

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

## Verification Steps

1. After implementing a fix, run the same command that failed in CI
2. Verify the specific test or task that failed now passes
3. If CI fails again with the same error, your fix was wrong — go back to Phase 1

## Pattern-Based Problems

When fixing issues caused by naming conventions or patterns:
1. Search the entire codebase for similar occurrences before making any changes
2. Fix ALL instances in a single commit
3. Never commit partial fixes for pattern-based problems
