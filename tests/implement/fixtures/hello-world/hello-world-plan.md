# Hello World — Implementation Plan

## Overview

Implement a minimal Spring Boot REST API with a single GET /hello endpoint.

## Thread 1: Hello World Endpoint

- [ ] **Task 1.1: Create Spring Boot application with GET /hello endpoint**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: GET /hello returns "Hello, World!" with HTTP 200
  - Evidence: Integration test passes — HTTP GET /hello returns 200 with body "Hello, World!"
  - Steps:
    - [ ] Create `src/main/java/com/example/hello/HelloWorldApplication.java` with `@SpringBootApplication`
    - [ ] Create `src/main/java/com/example/hello/HelloController.java` with `@GetMapping("/hello")` returning "Hello, World!"
    - [ ] Create `src/test/java/com/example/hello/HelloControllerTest.java` with MockMvc test
    - [ ] Create `.github/workflows/ci.yml` that runs `./gradlew build`
    - [ ] Verify `./gradlew build` passes
