# Platform Capability Specification: Build status badge service

## 1. Purpose and context

Repositories in the organization show their build status in their README. Today each README links to the GitHub Actions page. The badge service returns an SVG badge for a repository and branch.

## 2. Consumers

- README files of organization repositories, which embed the badge URL as an image.

## 3. Capabilities

- `GET /badge/{owner}/{repo}/{branch}.svg` returns an SVG badge.
- Green (`passing`) when the latest run concluded `success`, red (`failing`) when it concluded `failure`, grey (`unknown`) otherwise.

## 4. APIs, contracts and integration points

- Reads `GET /repos/{owner}/{repo}/actions/runs?branch={branch}&per_page=1` with the token in `BADGE_GITHUB_TOKEN`.
- Responds with `Content-Type: image/svg+xml` and HTTP 200 in every case.

## 5. Non-functional requirements

- Each repository and branch result is cached in memory for 60 seconds.
- A cached response is returned in under 50 ms.

## 6. Scenarios

1. A README requests the badge for a branch whose latest run succeeded; the service returns a green `passing` badge.
2. A README requests the badge for an unknown repository; the service returns a grey `unknown` badge with HTTP 200.

## 7. Constraints and assumptions

- GitHub Actions is the only CI system.

## 8. Acceptance criteria

1. Scenario 1 and scenario 2 pass in an automated end-to-end test.

## Change History
