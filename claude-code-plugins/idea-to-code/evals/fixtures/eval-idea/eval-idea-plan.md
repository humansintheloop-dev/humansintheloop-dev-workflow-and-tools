# Implementation Plan: Build status badge service

## Idea Type

**C. Platform/infrastructure capability**: a shared service that other repositories consume through a badge URL.

## Overview

A Python service built with FastAPI and tested with pytest. The project test command is `./test-scripts/test-end-to-end.sh`.

## Steel Thread 1: A README gets a badge for a passing branch

- [ ] **Task 1.1: The test script runs and the service starts**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: The script starts the service, calls `GET /health`, gets HTTP 200 and exits 0
  - Evidence: `./test-scripts/test-end-to-end.sh` exits 0 and prints `=== All Tests Passed ===`
  - Steps:
    - [ ] Create `pyproject.toml` with FastAPI and pytest
    - [ ] Create `src/badge/app.py` with `GET /health`
    - [ ] Create `test-scripts/test-end-to-end.sh`

- [ ] **Task 1.2: GET /badge returns a green passing badge when the latest run succeeded**
  - TaskType: OUTCOME
  - Entrypoint: `GET /badge/{owner}/{repo}/{branch}.svg`
  - Observable: The response has HTTP 200, `Content-Type: image/svg+xml` and an SVG containing `passing`
  - Evidence: `uv run pytest tests/test_badge.py -v` passes with a fake GitHub client whose latest run concluded `success`
  - Steps:
    - [ ] Write the failing test `tests/test_badge.py`
    - [ ] Add the `GET /badge/{owner}/{repo}/{branch}.svg` route to `src/badge/app.py`

## Change History
