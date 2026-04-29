# Fixing Stale SNAPSHOT Dependency Caches in GitHub Actions

When a Gradle build in GitHub Actions fails to resolve a SNAPSHOT dependency that works locally, the cause is usually stale dependency resolution metadata in the `gradle/actions/setup-gradle` cache.

## Symptoms

- **Missing newly added artifact**: `Could not find <group>:<artifact>:.` (empty version after the final colon) — the cached BOM was resolved before it included this artifact.
- **Stale SNAPSHOT version**: Build uses an outdated SNAPSHOT even though a newer one has been published — the cached resolution metadata points to the old timestamp.
- **Works locally, fails in CI**: Local builds resolve correctly because there's no stale cache (or `--refresh-dependencies` was used).

## Diagnosis

### Step 1: Verify the artifact exists remotely

```bash
curl -sI "https://<repo-url>/<group-as-path>/<artifact>/<version>/maven-metadata.xml"
```

A 200 response means the artifact is published — the problem is cache, not a missing artifact.

### Step 2: Verify local resolution

```bash
./gradlew dependencyInsight --configuration <config> --dependency <artifact> -p <project>
```

If it resolves correctly locally, the remote repository is fine.

### Step 3: Check CI cache restoration

```bash
gh run view <run-id> --log-failed 2>&1 | grep -i "cache"
```

Look for `Cache hit` and `Restored cache entry` lines, especially for `gradle-home-v1`. This cache restores `~/.gradle/caches` which contains dependency resolution metadata.

## Fix

Delete all `gradle-home` caches so Gradle re-resolves dependencies from scratch.

### Step 1: List all gradle-home caches

```bash
gh cache list --limit 1000 --key gradle-home --json id --jq '.[].id'
```

Use `--key` to filter server-side rather than grepping. Use `--limit 1000` because the default limit (30) may miss older entries. Do NOT use `--limit 0` — it is invalid.

### Step 2: Delete them all

```bash
gh cache list --limit 1000 --key gradle-home --json id --jq '.[].id' | xargs -I{} gh cache delete {}
```

### Step 3: Verify none remain

```bash
gh cache list --key gradle-home --limit 1000
```

This must return no results. The `gradle/actions/setup-gradle` action uses restore-key prefix matching — if even one old `gradle-home-v1` entry survives, it will be restored and the build will fail again.

### Step 4: Re-run the failed workflow

```bash
gh run rerun <run-id> --failed
```

## Why gradle-home specifically

The `gradle/actions/setup-gradle` action maintains several cache categories:

| Cache key prefix | Contents | Contains dependency metadata? |
|---|---|---|
| `gradle-home-v1` | `~/.gradle/caches`, notifications, setup | **Yes** — SNAPSHOT resolution timestamps and BOM metadata |
| `gradle-dependencies-v1` | `~/.gradle/caches/modules-*/files-*` | Artifact JARs only |
| `gradle-wrapper-zips-v1` | Gradle distribution | No |
| `gradle-transforms-v1` | Transform outputs | No |

Deleting `gradle-dependencies` alone is insufficient because SNAPSHOT resolution metadata (which version timestamp to use, which artifacts a BOM includes) is cached in `gradle-home`, not in `gradle-dependencies`.

## Common mistakes

- **Deleting only `gradle-dependencies` caches**: The stale metadata lives in `gradle-home`, not `gradle-dependencies`.
- **Using default `--limit`**: Old cache entries accumulate across branches and commits. Always use `--limit 1000`.
- **Not verifying all entries are deleted**: Restore-key prefix matching means a single surviving entry will be restored. Always verify with a follow-up list.
- **Claiming the artifact doesn't exist remotely**: Always verify with a direct HTTP request before concluding the artifact is unpublished.
- **Speculating beyond the evidence**: The CI log shows what caches were restored and what failed to resolve. Stick to what the log says — don't infer root causes that aren't supported by the evidence.
