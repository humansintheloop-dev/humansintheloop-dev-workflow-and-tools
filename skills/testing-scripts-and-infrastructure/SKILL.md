---
name: test-scripts-and-infrastructure
description: how to write tests (shell) scripts involving infrastructure
---

When writing tests for shell scripts or infrastructure:
- Tests MUST execute the script and verify the observable outcome
- Tests MUST NOT use grep/static analysis to check file contents
- Tests MUST NOT check for file existence as a proxy for correctness
- Before writing a test, state: "The observable outcome is: [X]"
- If a test can pass without running the code, it's not a behavioral test