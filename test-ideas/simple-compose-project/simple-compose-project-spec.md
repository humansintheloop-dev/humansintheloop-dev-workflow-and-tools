# Customer Service - Didactic Example Specification

## Overview

A comprehensive educational repository demonstrating Spring Boot REST API development with Docker Compose, JPA/Hibernate, and modern testing practices.

---

## Learning Goals

By studying and running this example, developers should be able to:

1. **Understand Spring Boot REST API fundamentals**
   - Create REST controllers with proper HTTP method mappings
   - Use DTOs and entity mapping patterns
   - Apply Bean Validation for input validation

2. **Master JPA/Hibernate basics**
   - Define JPA entities with annotations
   - Use `@Embedded`/`@Embeddable` for value objects
   - Implement Spring Data JPA repositories
   - Understand automatic schema generation with `ddl-auto`

3. **Configure Docker Compose for development**
   - Set up multi-container applications
   - Configure container networking between services
   - Build and run Spring Boot applications in containers

4. **Apply modern testing practices**
   - Write unit tests with Mockito for service layer isolation
   - Use `@WebMvcTest` for controller slice testing
   - Implement integration tests with Testcontainers for real database testing

---

## Concepts and Patterns Demonstrated

### Domain Modeling

| Concept | Implementation |
|---------|----------------|
| JPA Entity | `Customer` class with `@Entity` annotation |
| Primary Key | Auto-generated `Long id` with `@Id` and `@GeneratedValue` |
| Embedded Value Object | `Address` class with `@Embeddable` |
| Audit Fields | `createdAt` and `updatedAt` timestamps |

### Customer Entity Structure

```
Customer
├── id: Long (PK, auto-generated)
├── name: String (required)
├── email: String (required, valid email format)
├── phone: String (optional)
├── createdAt: Instant (auto-set on create)
├── updatedAt: Instant (auto-set on update)
└── address: Address (embedded)
    ├── street: String
    ├── city: String
    ├── state: String
    ├── zipCode: String
    └── country: String
```

### REST API Design

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/customers` | GET | List all customers |
| `/customers/{id}` | GET | Get customer by ID |
| `/customers` | POST | Create new customer |
| `/customers/{id}` | PUT | Update existing customer |
| `/customers/{id}` | DELETE | Delete customer |

### Validation Rules

| Field | Constraints |
|-------|-------------|
| `name` | `@NotNull`, `@Size(min=1, max=100)` |
| `email` | `@NotNull`, `@Email` |
| `phone` | `@Size(max=20)` (optional) |
| `address.zipCode` | `@Size(max=10)` |
| `address.country` | `@Size(max=50)` |

### Testing Pyramid

| Layer | Technology | Purpose |
|-------|------------|---------|
| Unit Tests | JUnit 5 + Mockito | Test service logic with mocked dependencies |
| Slice Tests | `@WebMvcTest` | Test controllers in isolation |
| Integration Tests | `@SpringBootTest` + Testcontainers | Test full stack with real Postgres |

### Infrastructure

| Component | Technology |
|-----------|------------|
| Application | Spring Boot 3.4.7 container |
| Database | Postgres container |
| Orchestration | Docker Compose |
| Build | Gradle with Groovy DSL |

---

## End-to-End Example Flows

### Flow 1: Create and Retrieve a Customer

1. User sends POST request to `/customers` with customer JSON
2. Application validates input using Bean Validation
3. Application persists customer to Postgres via JPA
4. Application returns created customer with generated ID
5. User sends GET request to `/customers/{id}`
6. Application retrieves customer from database
7. Application returns customer JSON

### Flow 2: Update Customer Address

1. User sends GET request to `/customers/{id}` to retrieve existing customer
2. User modifies address fields in the response
3. User sends PUT request to `/customers/{id}` with updated JSON
4. Application validates and persists changes
5. Application returns updated customer

### Flow 3: List and Delete Customers

1. User sends GET request to `/customers` to list all customers
2. Application returns array of all customers
3. User identifies customer to delete
4. User sends DELETE request to `/customers/{id}`
5. Application removes customer from database
6. Application returns 204 No Content

---

## Capabilities

### Must Have

1. **Gradle build configuration**
   - Spring Boot 3.4.7 parent
   - Java 23 toolchain
   - Dependencies: Spring Web, Spring Data JPA, Postgres driver, Validation, Testcontainers

2. **Docker Compose setup**
   - Postgres service with volume for data persistence
   - Spring Boot application service
   - Network configuration for inter-container communication
   - Application waits for database availability

3. **Dockerfile for Spring Boot application**
   - Multi-stage build (build stage + runtime stage)
   - Optimized layer caching

4. **JPA Entity classes**
   - `Customer` entity with all specified fields
   - `Address` embeddable value object

5. **Spring Data JPA Repository**
   - `CustomerRepository` extending `JpaRepository`

6. **REST Controller**
   - `CustomerController` with all CRUD endpoints
   - Request validation with `@Valid`

7. **Service Layer**
   - `CustomerService` with business logic
   - Proper exception handling for not-found scenarios

8. **Test Suite**
   - `CustomerServiceTest` - unit tests with Mockito
   - `CustomerControllerTest` - slice tests with `@WebMvcTest`
   - `CustomerIntegrationTest` - integration tests with Testcontainers

### Out of Scope

- Custom error handling with `@ControllerAdvice`
- Pagination and sorting
- Search/filter endpoints
- Database migrations (Flyway/Liquibase)
- Sample/seed data
- Security/authentication
- API documentation (OpenAPI/Swagger)
- Caching
- Logging configuration beyond defaults

---

## Constraints

1. **Java Version**: Java 23
2. **Spring Boot Version**: 3.4.7
3. **Build Tool**: Gradle with Groovy DSL
4. **Database**: Postgres (latest stable image)
5. **Schema Management**: Hibernate `ddl-auto=update` (no migrations)
6. **Package Structure**: `com.example.customerservice`

---

## Project Structure

```
customer-service/
├── build.gradle
├── settings.gradle
├── docker-compose.yml
├── Dockerfile
└── src/
    ├── main/
    │   ├── java/
    │   │   └── com/example/customerservice/
    │   │       ├── CustomerServiceApplication.java
    │   │       ├── domain/
    │   │       │   ├── Customer.java
    │   │       │   └── Address.java
    │   │       ├── repository/
    │   │       │   └── CustomerRepository.java
    │   │       ├── service/
    │   │       │   └── CustomerService.java
    │   │       └── controller/
    │   │           └── CustomerController.java
    │   └── resources/
    │       └── application.yml
    └── test/
        └── java/
            └── com/example/customerservice/
                ├── service/
                │   └── CustomerServiceTest.java
                ├── controller/
                │   └── CustomerControllerTest.java
                └── integration/
                    └── CustomerIntegrationTest.java
```

---

## Scenarios for Steel-Thread Planning

These scenarios define the runnable demonstrations that users of this example should be able to execute.

### Primary Scenario: Full CRUD Cycle via Docker Compose

**Precondition**: Docker and Docker Compose installed

**Steps**:
1. Clone repository
2. Run `docker compose up --build`
3. Wait for application to start
4. Create a customer via POST `/customers`
5. Retrieve the customer via GET `/customers/{id}`
6. Update the customer via PUT `/customers/{id}`
7. List all customers via GET `/customers`
8. Delete the customer via DELETE `/customers/{id}`
9. Verify deletion via GET `/customers/{id}` returns 404

**Success Criteria**: All operations complete successfully with expected HTTP status codes and response bodies.

### Secondary Scenario: Run Test Suite

**Precondition**: Java 23 and Docker installed

**Steps**:
1. Clone repository
2. Run `./gradlew test`
3. Observe unit tests pass (service layer)
4. Observe slice tests pass (controller layer)
5. Observe integration tests pass (Testcontainers spins up Postgres)

**Success Criteria**: All tests pass, demonstrating the testing pyramid.

### Tertiary Scenario: Local Development without Docker

**Precondition**: Java 23, Gradle, and local Postgres (or Postgres container) available

**Steps**:
1. Start Postgres database
2. Configure `application.yml` with database connection
3. Run `./gradlew bootRun`
4. Execute CRUD operations against `http://localhost:8080`

**Success Criteria**: Application runs locally and connects to external database.

---

## Acceptance Criteria

The example repository is complete when:

1. **Build succeeds**: `./gradlew build` completes without errors
2. **Tests pass**: All unit, slice, and integration tests pass
3. **Docker Compose works**: `docker compose up --build` starts both containers
4. **API functional**: All five CRUD endpoints work correctly
5. **Validation works**: Invalid input returns 400 Bad Request with validation errors
6. **Code is readable**: Code follows standard Spring Boot conventions and is self-documenting

---

## Change History

### 2026-02-02: Switch from Kotlin DSL to Groovy DSL

Changed build tool from Gradle with Kotlin DSL (`build.gradle.kts`) to Gradle with Groovy DSL (`build.gradle`). User preference for Groovy syntax.
