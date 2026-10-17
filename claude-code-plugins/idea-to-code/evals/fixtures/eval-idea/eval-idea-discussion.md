# Discussion: Build status badge service

## Q1: Which CI system does the service read?

**Answer:** GitHub Actions only. The service calls `GET /repos/{owner}/{repo}/actions/runs?branch={branch}&per_page=1`.

## Q2: How does the service authenticate to GitHub?

**Answer:** With a GitHub App installation token read from the `BADGE_GITHUB_TOKEN` environment variable.

## Q3: How long may a badge be stale?

**Answer:** Up to 60 seconds. The service caches each repository and branch result in memory for 60 seconds.

## Q4: What does the service return when the repository is unknown?

**Answer:** A grey badge with the text `unknown` and HTTP status 200, so README images never break.

## Classification

**Type:** C. Platform/infrastructure capability

**Rationale:** The service is shared infrastructure that other repositories consume through a URL contract; it has no end-user interface of its own.
