# Simple Compose Project - Discussion

## Overview
Brainstorming and refinement discussion for a Customer Service REST API project.

## Initial Idea
- Customer Service with REST API for managing Customers
- Tech stack: Java, Gradle, JPA, Spring Boot, Postgres, Docker Compose

---

## Questions and Answers

### Q1: Classification - What is the primary purpose of this project?

**Answer:** D - Educational/example repository

---

### Q2: Learning Objectives - What concepts should this example demonstrate?

**Answer:** E - All of the above (comprehensive reference)
- Basic CRUD operations with Spring Boot REST API
- Docker Compose multi-service setup (Spring Boot + Postgres)
- JPA/Hibernate fundamentals (entity mapping, repositories)
- Testing patterns (unit tests, integration tests, testcontainers)

---

### Q3: Customer Entity - What attributes should the Customer have?

**Answer:** B + C - Standard fields with Address
- `id` (primary key)
- `name`
- `email`
- `phone`
- `createdAt`, `updatedAt` (audit fields)
- Address information

---

### Q4: Address Modeling - How should the Address be structured?

**Answer:** A - Embedded (`@Embeddable`)
- Address fields (street, city, state, zipCode, country) stored directly in the Customer table
- Demonstrates `@Embedded`/`@Embeddable` JPA pattern
- Simpler model appropriate for educational purposes

---

### Q5: REST API Operations - What endpoints should be exposed?

**Answer:** A - Basic CRUD only
- `GET /customers` - List all customers
- `GET /customers/{id}` - Get customer by ID
- `POST /customers` - Create new customer
- `PUT /customers/{id}` - Update existing customer
- `DELETE /customers/{id}` - Delete customer

---

### Q6: Testing Strategy - What types of tests should be demonstrated?

**Answer:** D - Full coverage (comprehensive testing pyramid)
- Unit tests for service layer with mocked repositories (Mockito)
- Controller slice tests with `@WebMvcTest` (isolated controller testing)
- Integration tests with `@SpringBootTest` and Testcontainers for Postgres (real database testing)

---

### Q7: Java Version - Which Java version should the project target?

**Answer:** Java 23 - Cutting edge, demonstrates newest language features

---

### Q8: Spring Boot Version - Which Spring Boot version?

**Answer:** Spring Boot 3.4.7

---

### Q9: Validation and Error Handling - How should input validation and errors be handled?

**Answer:** B - Standard validation
- Use Bean Validation annotations (`@NotNull`, `@Email`, `@Size`, etc.) with `@Valid`
- Default Spring error responses (no custom `@ControllerAdvice`)

---

### Q10: Docker Compose Setup - What should the compose environment include?

**Answer:** B - Full containerized
- Postgres container
- Spring Boot application container
- Demonstrates multi-container setup and Docker networking

---

### Q11: Database Initialization - Should there be sample data?

**Answer:** A - No sample data
- Empty database
- Schema created automatically by Hibernate `ddl-auto`

---

### Q12: Project Location - Where should the project be created?

**Answer:** Standalone project - The `make-plan.sh` script will be run in an empty root directory. The project files (build.gradle, src/, docker-compose.yml, etc.) will be created at the root of that directory.

---

### Q13: Project Naming - What should the Gradle artifact and package names be?

**Answer:** A - Simple defaults
- Group: `com.example`
- Artifact: `customer-service`
- Base package: `com.example.customerservice`

---

## Summary

**Classification:** Educational/example repository

**Purpose:** A comprehensive reference implementation demonstrating Spring Boot + Docker Compose patterns.

**Technical Decisions:**
- **Entity:** Customer with id, name, email, phone, createdAt, updatedAt, and embedded Address (street, city, state, zipCode, country)
- **API:** Basic CRUD - GET /customers, GET /customers/{id}, POST, PUT, DELETE
- **Testing:** Full coverage - unit tests (Mockito), controller slice tests (@WebMvcTest), integration tests (Testcontainers)
- **Stack:** Java 23, Spring Boot 3.4.7, Gradle, JPA/Hibernate, Postgres
- **Validation:** Bean Validation (@NotNull, @Email, @Size, etc.) with @Valid
- **Docker:** Full containerized setup (Postgres + Spring Boot app)
- **Database:** Schema via Hibernate ddl-auto, no sample data
- **Naming:** com.example / customer-service / com.example.customerservice

---

### Final Question: Additional Requirements

