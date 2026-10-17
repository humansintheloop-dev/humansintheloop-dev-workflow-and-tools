# Build status badge service

Add a small HTTP service that other repositories in the organization call to get an SVG build status badge. The service reads the latest GitHub Actions run for a repository and branch and returns a green, red or grey badge. Repositories embed the badge URL in their README.
