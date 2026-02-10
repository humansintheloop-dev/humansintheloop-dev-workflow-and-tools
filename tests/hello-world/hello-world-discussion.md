# HelloWorld Java — Discussion

## Classification

**Type:** D. Educational/example repository
**Rationale:** A self-contained educational example demonstrating how to set up a Java project from scratch.

## Questions & Answers

### Q1: What is the primary purpose of this HelloWorld Java project?
**Options:** A. Test fixture, B. Standalone example, C. Template/starter, D. Something else
**Answer:** B. Standalone example — a self-contained educational example demonstrating how to set up a Java project from scratch.

### Q2: Which build tool should the project use?
**Options:** A. Gradle (Groovy DSL), B. Gradle (Kotlin DSL), C. Maven, D. None (just javac/java)
**Answer:** A. Gradle (Groovy DSL)

### Q3: Should the project include a unit test?
**Options:** A. Include a unit test (JUnit 5), B. No tests
**Answer:** A. Include a unit test — demonstrates good practice even for a simple project.

### Q4: Should the project include a CI workflow?
**Options:** A. Include CI (GitHub Actions), B. No CI
**Answer:** A. Include CI — a GitHub Actions workflow for build + test.

### Q5: Where should the project be created?
**Answer:** Own repository. `idea-to-code.sh` will be run in the root directory of wherever the project should be created, so the project is standalone with its own Git history.
