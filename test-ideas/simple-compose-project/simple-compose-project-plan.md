# Customer Service - Implementation Plan

## Idea Type

**D. Educational/example repo** - This is a comprehensive reference implementation demonstrating Spring Boot + Docker Compose patterns for educational purposes.

---

## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Steel Thread 1: Foundation - Spring Boot App with Health Check, Docker Compose, and CI

This steel thread proves three things work together:
1. End-to-end flow: Spring Boot application responds to HTTP requests
2. Deployment pipeline: CI validates all commits via GitHub Actions
3. Deployment architecture: Docker Compose runs the application with Postgres

### Tasks

- [ ] **Task 1.1: Spring Boot application starts and responds to health check with Docker Compose infrastructure**
  - TaskType: INFRA
  - Entrypoint: `./gradlew build && ./test-scripts/test-end-to-end.sh`
  - Observable: Health endpoint returns 200 OK with `{"status":"UP"}` both via JUnit tests and via Docker Compose deployment
  - Evidence: CI runs `./gradlew build` and `./test-scripts/test-end-to-end.sh` and both pass
  - Steps:
    - [ ] Create `.gitignore` with standard Java/Gradle ignores (build/, .gradle/, *.class, .idea/, *.iml)
    - [ ] Create `settings.gradle` with project name `customer-service`
    - [ ] Create `build.gradle` with Spring Boot 3.4.7, Java 23, dependencies: spring-boot-starter-web, spring-boot-starter-actuator, spring-boot-starter-test
    - [ ] Run `gradle wrapper --gradle-version 8.11.1` to generate wrapper files
    - [ ] Create `src/main/java/com/example/customerservice/CustomerServiceApplication.java` with `@SpringBootApplication`
    - [ ] Create `src/main/resources/application.yml` with actuator health endpoint enabled
    - [ ] Create `src/test/java/com/example/customerservice/HealthCheckTest.java` that uses `@SpringBootTest(webEnvironment = RANDOM_PORT)` and `TestRestTemplate` to GET `/actuator/health` and assert 200 with status UP
    - [ ] Create `Dockerfile` that copies pre-built JAR (simple, not multi-stage build with Gradle)
    - [ ] Create `docker-compose.yml` with postgres and app services, app depends on postgres with healthcheck
    - [ ] Create `test-scripts/test-cleanup.sh` that runs `docker compose down -v --remove-orphans`
    - [ ] Create `test-scripts/test-docker-health.sh` that runs `docker compose up --build -d`, waits for health, curls `/actuator/health`, asserts 200, runs `docker compose down`
    - [ ] Create `test-scripts/test-end-to-end.sh` that runs cleanup then all test scripts
    - [ ] Create `.github/workflows/ci.yml` that runs `./gradlew build` and `./test-scripts/test-end-to-end.sh`

---

## Steel Thread 2: Create Customer (POST /customers)

Implements the first CRUD operation: creating a new customer with validation.

### Tasks

- [ ] **Task 2.1: POST /customers creates a customer and persists to Postgres**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: POST `/customers` with valid JSON returns 201 Created with the customer including generated ID, and the customer is persisted to the database
  - Evidence: Integration test using Testcontainers creates a customer via POST and verifies the response and database state
  - Steps:
    - [ ] Add dependencies to `build.gradle`: spring-boot-starter-data-jpa, spring-boot-starter-validation, postgresql driver, testcontainers (postgres, junit-jupiter)
    - [ ] Create `src/main/java/com/example/customerservice/domain/Address.java` as `@Embeddable` with fields: street, city, state, zipCode (`@Size(max=10)`), country (`@Size(max=50)`)
    - [ ] Create `src/main/java/com/example/customerservice/domain/Customer.java` as `@Entity` with: id (Long, `@Id`, `@GeneratedValue`), name (`@NotNull`, `@Size(min=1, max=100)`), email (`@NotNull`, `@Email`), phone (`@Size(max=20)`), createdAt/updatedAt (Instant), address (`@Embedded`)
    - [ ] Create `src/main/java/com/example/customerservice/repository/CustomerRepository.java` extending `JpaRepository<Customer, Long>`
    - [ ] Create `src/main/java/com/example/customerservice/service/CustomerService.java` with `createCustomer(Customer)` method that sets timestamps and saves
    - [ ] Create `src/main/java/com/example/customerservice/controller/CustomerController.java` with `@PostMapping("/customers")` that validates (`@Valid`) and returns 201
    - [ ] Update `src/main/resources/application.yml` with JPA/Postgres configuration and `ddl-auto: update`
    - [ ] Create `src/test/java/com/example/customerservice/integration/CustomerIntegrationTest.java` using `@SpringBootTest` with Testcontainers Postgres to test POST creates customer
    - [ ] Update `test-scripts/test-docker-health.sh` to also POST a test customer and verify 201 response

- [ ] **Task 2.2: POST /customers returns 400 for invalid input**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: POST `/customers` with invalid data (missing name, invalid email) returns 400 Bad Request
  - Evidence: Controller slice test with `@WebMvcTest` verifies 400 response for invalid input
  - Steps:
    - [ ] Create `src/test/java/com/example/customerservice/controller/CustomerControllerTest.java` with `@WebMvcTest` that tests invalid input returns 400
    - [ ] Verify validation annotations on entity are enforced by the controller

---

## Steel Thread 3: Get Customer (GET /customers/{id})

Implements retrieving a single customer by ID.

### Tasks

- [ ] **Task 3.1: GET /customers/{id} returns existing customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: GET `/customers/{id}` for existing customer returns 200 OK with customer JSON
  - Evidence: Integration test creates customer, then retrieves by ID and verifies response
  - Steps:
    - [ ] Add `findById(Long)` method to `CustomerService` returning `Optional<Customer>`
    - [ ] Add `@GetMapping("/customers/{id}")` to `CustomerController` that returns customer or 404
    - [ ] Add test to `CustomerIntegrationTest.java` that creates customer and retrieves by ID

- [ ] **Task 3.2: GET /customers/{id} returns 404 for non-existent customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: GET `/customers/{id}` for non-existent ID returns 404 Not Found
  - Evidence: Integration test requests non-existent ID and verifies 404 response
  - Steps:
    - [ ] Add test to `CustomerIntegrationTest.java` for 404 case
    - [ ] Verify controller returns 404 when service returns empty Optional

---

## Steel Thread 4: List Customers (GET /customers)

Implements listing all customers.

### Tasks

- [ ] **Task 4.1: GET /customers returns all customers**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: GET `/customers` returns 200 OK with array of all customers
  - Evidence: Integration test creates multiple customers, then lists and verifies all are returned
  - Steps:
    - [ ] Add `findAll()` method to `CustomerService`
    - [ ] Add `@GetMapping("/customers")` to `CustomerController`
    - [ ] Add test to `CustomerIntegrationTest.java` that creates multiple customers and lists all
    - [ ] Update `test-scripts/test-docker-health.sh` to verify GET /customers returns array

---

## Steel Thread 5: Update Customer (PUT /customers/{id})

Implements updating an existing customer.

### Tasks

- [ ] **Task 5.1: PUT /customers/{id} updates existing customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: PUT `/customers/{id}` with valid JSON updates the customer and returns 200 OK with updated data, updatedAt timestamp is modified
  - Evidence: Integration test creates customer, updates via PUT, verifies response and database state
  - Steps:
    - [ ] Add `updateCustomer(Long, Customer)` method to `CustomerService` that updates fields and sets updatedAt
    - [ ] Add `@PutMapping("/customers/{id}")` to `CustomerController` with `@Valid`
    - [ ] Add test to `CustomerIntegrationTest.java` that creates, updates, and verifies

- [ ] **Task 5.2: PUT /customers/{id} returns 404 for non-existent customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: PUT `/customers/{id}` for non-existent ID returns 404 Not Found
  - Evidence: Integration test attempts to update non-existent ID and verifies 404
  - Steps:
    - [ ] Add test to `CustomerIntegrationTest.java` for 404 case on update
    - [ ] Verify service/controller handles non-existent customer correctly

- [ ] **Task 5.3: PUT /customers/{id} returns 400 for invalid input**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: PUT `/customers/{id}` with invalid data returns 400 Bad Request
  - Evidence: Controller slice test verifies 400 response for invalid update input
  - Steps:
    - [ ] Add test to `CustomerControllerTest.java` for invalid update input

---

## Steel Thread 6: Delete Customer (DELETE /customers/{id})

Implements deleting a customer.

### Tasks

- [ ] **Task 6.1: DELETE /customers/{id} removes existing customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: DELETE `/customers/{id}` removes the customer and returns 204 No Content, subsequent GET returns 404
  - Evidence: Integration test creates customer, deletes, verifies 204, then verifies GET returns 404
  - Steps:
    - [ ] Add `deleteCustomer(Long)` method to `CustomerService`
    - [ ] Add `@DeleteMapping("/customers/{id}")` to `CustomerController` returning 204
    - [ ] Add test to `CustomerIntegrationTest.java` that creates, deletes, and verifies removal
    - [ ] Update `test-scripts/test-docker-health.sh` to test full CRUD cycle including delete

- [ ] **Task 6.2: DELETE /customers/{id} returns 404 for non-existent customer**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: DELETE `/customers/{id}` for non-existent ID returns 404 Not Found
  - Evidence: Integration test attempts to delete non-existent ID and verifies 404
  - Steps:
    - [ ] Add test to `CustomerIntegrationTest.java` for 404 case on delete

---

## Steel Thread 7: Service Layer Unit Tests

Adds unit tests with Mockito for the service layer, completing the testing pyramid.

### Tasks

- [ ] **Task 7.1: CustomerService unit tests with mocked repository**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: Unit tests verify service business logic with mocked CustomerRepository
  - Evidence: `CustomerServiceTest.java` passes with tests for all service methods
  - Steps:
    - [ ] Create `src/test/java/com/example/customerservice/service/CustomerServiceTest.java` with `@ExtendWith(MockitoExtension.class)`
    - [ ] Add unit tests for: createCustomer (sets timestamps), findById, findAll, updateCustomer (updates timestamp), deleteCustomer
    - [ ] Verify all tests pass with `./gradlew test`

---

## Summary

This plan implements the Customer Service educational example through 7 steel threads:

1. **Foundation**: Spring Boot + Docker Compose + CI (proves all three pillars work together)
2. **Create Customer**: POST with validation
3. **Get Customer**: GET by ID with 404 handling
4. **List Customers**: GET all
5. **Update Customer**: PUT with validation and 404 handling
6. **Delete Customer**: DELETE with 204/404 handling
7. **Service Unit Tests**: Complete testing pyramid with Mockito

Each task follows TDD practices and includes its own tests. The plan builds incrementally, adding dependencies and directories only when needed.
