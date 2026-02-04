# Customer Service - Design Document

## 1. Overview

### Summary

A comprehensive educational repository demonstrating Spring Boot REST API development with Docker Compose, JPA/Hibernate, and modern testing practices. The application provides a CRUD API for managing Customer entities with embedded Address information.

### Key Goals

1. **Educational Value**: Serve as a reference implementation for developers learning Spring Boot patterns
2. **Complete Testing Pyramid**: Demonstrate unit, slice, and integration testing approaches
3. **Production-Like Deployment**: Show containerized multi-service setup with Docker Compose
4. **Simplicity**: Keep the domain simple to focus on infrastructure and patterns

### Constraints

| Constraint | Value |
|------------|-------|
| Java Version | 23 |
| Spring Boot Version | 3.4.7 |
| Build Tool | Gradle with Groovy DSL |
| Database | Postgres (containerized) |
| Schema Management | Hibernate ddl-auto (no migrations) |

---

## 2. Domain View

### Domain Concepts

This is a single-subdomain application with one aggregate root:

```
┌─────────────────────────────────────────┐
│           Customer (Aggregate Root)      │
├─────────────────────────────────────────┤
│ - id: Long (PK)                         │
│ - name: String                          │
│ - email: String                         │
│ - phone: String                         │
│ - createdAt: Instant                    │
│ - updatedAt: Instant                    │
│ - address: Address (embedded)           │
└─────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│           Address (Value Object)         │
├─────────────────────────────────────────┤
│ - street: String                        │
│ - city: String                          │
│ - state: String                         │
│ - zipCode: String                       │
│ - country: String                       │
└─────────────────────────────────────────┘
```

### Package Structure

```
com.example.customerservice/
├── CustomerServiceApplication.java    # Spring Boot entry point
├── domain/
│   ├── Customer.java                  # JPA entity (aggregate root)
│   └── Address.java                   # @Embeddable value object
├── repository/
│   └── CustomerRepository.java        # Spring Data JPA repository
├── service/
│   └── CustomerService.java           # Business logic layer
└── controller/
    └── CustomerController.java        # REST API endpoints
```

### Domain Patterns

| Pattern | Implementation |
|---------|----------------|
| Aggregate Root | `Customer` entity owns `Address` |
| Value Object | `Address` as `@Embeddable` (no identity) |
| Repository | Spring Data JPA `JpaRepository` |
| Service Layer | `CustomerService` encapsulates business logic |

### Validation Rules

| Field | Constraints |
|-------|-------------|
| `name` | Required, 1-100 characters |
| `email` | Required, valid email format |
| `phone` | Optional, max 20 characters |
| `address.zipCode` | Max 10 characters |
| `address.country` | Max 50 characters |

---

## 3. Component View

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                    Customer Service                           │
│                    (Spring Boot Application)                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  Controller │───▶│   Service   │───▶│   Repository    │  │
│  │    Layer    │    │    Layer    │    │     Layer       │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│        │                                       │             │
│        ▼                                       ▼             │
│  ┌─────────────┐                      ┌─────────────────┐   │
│  │    Bean     │                      │   JPA/Hibernate │   │
│  │ Validation  │                      │                 │   │
│  └─────────────┘                      └─────────────────┘   │
│                                               │              │
└───────────────────────────────────────────────┼──────────────┘
                                                │
                                                ▼
                                    ┌─────────────────────┐
                                    │     PostgreSQL      │
                                    │     Database        │
                                    └─────────────────────┘
```

### API Surface

| Endpoint | Method | Request Body | Response |
|----------|--------|--------------|----------|
| `/customers` | GET | - | List of customers |
| `/customers/{id}` | GET | - | Single customer or 404 |
| `/customers` | POST | Customer JSON | Created customer with ID |
| `/customers/{id}` | PUT | Customer JSON | Updated customer |
| `/customers/{id}` | DELETE | - | 204 No Content |

### Layer Responsibilities

| Layer | Responsibility |
|-------|----------------|
| Controller | HTTP request/response handling, input validation |
| Service | Business logic, transaction management |
| Repository | Data access, persistence |

---

## 4. Deployment View

### Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────┐    ┌───────────────────────┐    │
│  │   customer-service    │    │      postgres         │    │
│  │   (Spring Boot app)   │───▶│    (Database)         │    │
│  │                       │    │                       │    │
│  │   Port: 8080          │    │   Port: 5432          │    │
│  │   Image: built        │    │   Image: postgres     │    │
│  └───────────────────────┘    └───────────────────────┘    │
│            │                            │                   │
│            ▼                            ▼                   │
│      [host:8080]                  [named volume]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Infrastructure Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Application Runtime | JVM 23 in container | Run Spring Boot application |
| Database | PostgreSQL (latest) | Persistent data storage |
| Orchestration | Docker Compose | Multi-container management |
| Networking | Docker bridge network | Inter-container communication |

### Application Configuration

```yaml
# application.yml structure
spring:
  datasource:
    url: jdbc:postgresql://postgres:5432/customerdb
    username: ${DB_USER}
    password: ${DB_PASSWORD}
  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
```

### Health and Observability

| Aspect | Implementation |
|--------|----------------|
| Health Check | Spring Actuator `/actuator/health` |
| Database Health | Auto-configured by Spring Data JPA |
| Startup Dependency | Docker Compose `depends_on` with health check |

---

## 5. Build View

### Source Repository Structure

```
customer-service/
├── build.gradle              # Gradle build configuration
├── settings.gradle           # Project settings
├── docker-compose.yml        # Multi-container orchestration
├── Dockerfile                # Application container build
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions CI pipeline
└── src/
    ├── main/
    │   ├── java/...          # Application source
    │   └── resources/
    │       └── application.yml
    └── test/
        └── java/...          # Test source
```

### Build Configuration

```groovy
// build.gradle key elements
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.4.7'
    id 'io.spring.dependency-management'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(23)
    }
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    runtimeOnly 'org.postgresql:postgresql'

    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.testcontainers:postgresql'
    testImplementation 'org.testcontainers:junit-jupiter'
}
```

### Dockerfile Strategy

Multi-stage build for optimized images:

```dockerfile
# Stage 1: Build
FROM eclipse-temurin:23-jdk AS builder
WORKDIR /app
COPY . .
RUN ./gradlew bootJar --no-daemon

# Stage 2: Runtime
FROM eclipse-temurin:23-jre
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

### CI/CD Pipeline

```
┌─────────┐    ┌─────────┐    ┌─────────────┐    ┌────────────┐
│ Commit  │───▶│  Build  │───▶│    Test     │───▶│   Docker   │
│         │    │         │    │             │    │   Build    │
└─────────┘    └─────────┘    └─────────────┘    └────────────┘
                    │               │
                    ▼               ▼
              Compile Java    Unit Tests
              Check style     Slice Tests
                              Integration Tests
                              (Testcontainers)
```

### Testing Strategy

| Test Type | Framework | Scope | Database |
|-----------|-----------|-------|----------|
| Unit Tests | JUnit 5 + Mockito | Service layer | Mocked |
| Slice Tests | @WebMvcTest | Controller layer | None (mocked service) |
| Integration Tests | @SpringBootTest + Testcontainers | Full stack | Real Postgres container |

### Test Classes

| Class | Purpose |
|-------|---------|
| `CustomerServiceTest` | Unit tests for business logic |
| `CustomerControllerTest` | Slice tests for REST endpoints |
| `CustomerIntegrationTest` | End-to-end tests with real database |

---

## 6. Key Design Decisions

### Decision 1: Embedded Address vs. Separate Entity

**Choice**: `@Embeddable` Address stored in Customer table

**Rationale**:
- Simpler schema (single table)
- Demonstrates JPA embedding pattern
- Address has no independent lifecycle
- Appropriate for educational simplicity

**Trade-off**: Cannot share addresses between customers or query addresses independently

### Decision 2: No DTO Layer

**Choice**: Use entities directly in REST responses (with `@JsonIgnore` where needed)

**Rationale**:
- Reduces boilerplate in a simple CRUD application
- Entity structure matches API contract
- Focus on core patterns rather than mapping

**Trade-off**: Tighter coupling between domain and API

### Decision 3: Hibernate ddl-auto vs. Migrations

**Choice**: Use `hibernate.ddl-auto=update` for schema management

**Rationale**:
- Simpler setup for educational purposes
- No migration scripts to maintain
- Suitable for development/demo scenarios

**Trade-off**: Not production-safe; schema changes aren't versioned

### Decision 4: Single Service, No Decomposition

**Choice**: Monolithic service containing all layers

**Rationale**:
- Focus on vertical patterns (controller→service→repository)
- Avoid microservice complexity for educational example
- Single deployment unit simplifies Docker Compose

### Decision 5: Testcontainers for Integration Tests

**Choice**: Use Testcontainers instead of H2 or embedded database

**Rationale**:
- Tests against real Postgres (same as production)
- Demonstrates modern testing practices
- Catches database-specific issues early

---

## 7. Technical Risks and Mitigations

### Risk 1: Java 23 Compatibility

**Risk**: Java 23 is very recent; some tooling may have issues

**Mitigation**:
- Use official Eclipse Temurin images
- Verify Gradle and Spring Boot support before starting

### Risk 2: Testcontainers Requires Docker

**Risk**: CI environment must have Docker for integration tests

**Mitigation**:
- GitHub Actions runners have Docker pre-installed
- Document Docker requirement clearly

### Risk 3: Container Startup Timing

**Risk**: Application may start before database is ready

**Mitigation**:
- Use Docker Compose `depends_on` with health check condition
- Spring Boot retry for database connection

---

## 8. Open Questions

None identified. The specification is complete and all design decisions have been made.

---

## Change History

### 2026-02-04: Initial design document

Created design document based on specification covering all architectural views for the Customer Service educational example.
