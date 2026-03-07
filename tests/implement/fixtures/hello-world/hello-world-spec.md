# Hello World — Specification

## Purpose

A minimal Spring Boot REST API that returns "Hello, World!" from a GET endpoint.

## Technology

- Java 21
- Spring Boot 3.x
- Gradle build system

## Functional Requirements

### FR-1: GET /hello endpoint

- **Method:** GET
- **Path:** /hello
- **Response:** Plain text "Hello, World!" with HTTP 200

## Non-Functional Requirements

### NFR-1: CI Pipeline

- GitHub Actions CI workflow at `.github/workflows/ci.yml`
- Runs `./gradlew build` on push and PR
