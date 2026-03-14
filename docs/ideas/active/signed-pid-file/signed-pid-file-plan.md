I have the spec and idea files. The spec provides enough detail about the CLI patterns (Click-based, subcommand groups in `cli.py`). Let me generate the plan.

## Idea Type: C — Platform/infrastructure capability

# Signed PID File — Implementation Plan

## Idea Type

**C. Platform/infrastructure capability** — Adds digital signature security to `pid.yaml` configuration files in the i2code/isolarium platform.

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
- Before using Write on any production `.py` file in `src/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Steel Thread 1: Key Generation Produces Valid Ed25519 Key Pair

This thread proves the `i2code pid keygen` subcommand works end-to-end: the `pid` subcommand group is registered in the CLI, the `keygen` command generates valid Ed25519 keys, and CI validates everything.

- [ ] **Task 1.1: `i2code pid keygen` generates Ed25519 key pair and env script**
  - TaskType: INFRA
  - Entrypoint: `i2code pid keygen --key-id test-key --output-dir /tmp/test-keys`
  - Observable: Three files created — `test-key-private.pem` (Ed25519 private key, mode 0600), `test-key-public.pem` (Ed25519 public key), `test-key-env.sh` (exports `PID_FILE_SIGNING_KEY` and `PID_VERIFY_KEY_test-key`)
  - Evidence: `pytest` tests verify key generation produces valid PEM-encoded Ed25519 keys, correct file permissions, and correct env script content; CI runs tests and passes
  - Steps:
    - [ ] Add `cryptography` to project dependencies in `pyproject.toml`
    - [ ] Create `src/i2code/pid/__init__.py` (empty package init)
    - [ ] Create `src/i2code/pid/cli.py` with Click group `pid` and `keygen` subcommand
    - [ ] Register the `pid` group in `src/i2code/cli.py` (main CLI entry point)
    - [ ] Implement `src/i2code/pid/keygen.py` — Ed25519 key pair generation using `cryptography` library, PEM encoding, file permissions, env script generation
    - [ ] Create `tests/pid/test_keygen.py` with tests:
      - Generates three output files with correct names
      - Private key file has mode 0600
      - Private key is valid PEM-encoded Ed25519 private key
      - Public key is valid PEM-encoded Ed25519 public key
      - Env script exports correct variables with correct values
      - Output directory is created if it does not exist
    - [ ] Create `test-scripts/test-pid-keygen.sh` — runs `i2code pid keygen`, verifies output files exist
    - [ ] Create `test-scripts/test-end-to-end.sh` — runs cleanup then `test-pid-keygen.sh`
    - [ ] Create `test-scripts/test-cleanup.sh` — removes temporary test artifacts
    - [ ] Update `.github/workflows/ci.yml` to also run `./test-scripts/test-end-to-end.sh`

- [ ] **Task 1.2: `keygen` refuses to overwrite existing key files**
  - TaskType: OUTCOME
  - Entrypoint: `i2code pid keygen --key-id existing-key --output-dir /tmp/test-keys` (where files already exist)
  - Observable: Command exits with non-zero exit code, error message indicates file already exists, no files are overwritten
  - Evidence: `pytest` test generates keys, runs keygen again with same key-id, asserts non-zero exit code and original file contents unchanged
  - Steps:
    - [ ] Add overwrite-protection logic to `src/i2code/pid/keygen.py` — check for existing files before writing
    - [ ] Add test in `tests/pid/test_keygen.py` — verifies error on existing files, verifies files unchanged

---

## Steel Thread 2: Sign a PID File

This thread implements `i2code pid sign` — signing a `pid.yaml` with an Ed25519 private key.

- [ ] **Task 2.1: `i2code pid sign` signs an unsigned `pid.yaml`**
  - TaskType: OUTCOME
  - Entrypoint: `PID_FILE_SIGNING_KEY=<pem-key> i2code pid sign --key-id test-key path/to/pid.yaml`
  - Observable: `pid.yaml` is rewritten with original content followed by `\n---\n` and a signature YAML document containing `signature.algorithm: Ed25519`, `signature.key_id: test-key`, and `signature.value: <base64-encoded-signature>`. The signature is a valid Ed25519 signature of the first document's raw bytes.
  - Evidence: `pytest` test creates a `pid.yaml`, signs it, parses the output file, verifies two YAML documents exist, verifies the signature is cryptographically valid against the first document's raw bytes using the corresponding public key
  - Steps:
    - [ ] Create `src/i2code/pid/sign.py` — implements signing logic: read file, extract first document bytes, load private key from env var, sign with Ed25519, write file with signature document appended
    - [ ] Add `sign` subcommand to `src/i2code/pid/cli.py`
    - [ ] Create `tests/pid/test_sign.py` with tests:
      - Signs an unsigned `pid.yaml` and appends valid signature document
      - Signature is cryptographically valid (verify with public key)
      - First document content is preserved byte-for-byte
      - Default path is `./pid.yaml` when path argument omitted

- [ ] **Task 2.2: `sign` replaces existing signature (re-signing)**
  - TaskType: OUTCOME
  - Entrypoint: `PID_FILE_SIGNING_KEY=<pem-key> i2code pid sign --key-id test-key path/to/pid.yaml` (on an already-signed file)
  - Observable: The existing signature document is replaced with a new valid signature; only two YAML documents exist in the file (no accumulation of signature documents)
  - Evidence: `pytest` test signs a file, modifies the first document, re-signs, verifies the new signature is valid and only one signature document exists
  - Steps:
    - [ ] Update `src/i2code/pid/sign.py` — strip existing second document before signing
    - [ ] Add tests in `tests/pid/test_sign.py`:
      - Re-signing an already-signed file replaces the signature
      - Re-signing after content change produces valid signature for new content
      - File contains exactly two YAML documents after re-signing

- [ ] **Task 2.3: `sign` reports clear errors for invalid inputs**
  - TaskType: OUTCOME
  - Entrypoint: `i2code pid sign --key-id test-key path/to/pid.yaml` (with various invalid inputs)
  - Observable: Non-zero exit code and actionable error message for each error condition: missing env var, invalid PEM key, missing file, invalid YAML
  - Evidence: `pytest` tests for each error condition verify exit code and error message content
  - Steps:
    - [ ] Add error handling to `src/i2code/pid/sign.py` for all error conditions specified in the spec
    - [ ] Add tests in `tests/pid/test_sign.py`:
      - Missing `PID_FILE_SIGNING_KEY` env var → error with message
      - Invalid PEM key in env var → error with message
      - Non-existent file path → error with message
      - Invalid YAML content → error with message

---

## Steel Thread 3: Verify a PID File Signature

This thread implements `i2code pid verify-signature` — verifying the signature on a `pid.yaml`.

- [ ] **Task 3.1: `verify-signature` validates a correctly signed file**
  - TaskType: OUTCOME
  - Entrypoint: `PID_VERIFY_KEY_test_key=<pem-public-key> i2code pid verify-signature path/to/pid.yaml`
  - Observable: Exit code `0`, stdout prints `pid.yaml: signature valid (key_id: test-key, algorithm: Ed25519)`
  - Evidence: `pytest` test generates keys, signs a `pid.yaml`, runs verify-signature, asserts exit code 0 and correct output message
  - Steps:
    - [ ] Create `src/i2code/pid/verify.py` — implements verification logic: read file, split on `---`, parse signature document, look up public key from env var, verify Ed25519 signature
    - [ ] Add `verify-signature` subcommand to `src/i2code/pid/cli.py`
    - [ ] Create `tests/pid/test_verify.py` with tests:
      - Valid signed file returns exit code 0 with correct success message
      - Default path is `./pid.yaml` when path argument omitted
    - [ ] Create `test-scripts/test-pid-sign-verify.sh` — end-to-end: keygen, sign, verify-signature (exits 0)
    - [ ] Add `test-pid-sign-verify.sh` to `test-scripts/test-end-to-end.sh`

- [ ] **Task 3.2: `verify-signature` detects tampered files**
  - TaskType: OUTCOME
  - Entrypoint: `PID_VERIFY_KEY_test_key=<pem-public-key> i2code pid verify-signature path/to/pid.yaml` (where first document has been modified after signing)
  - Observable: Exit code `1`, stdout prints `pid.yaml: signature verification failed`
  - Evidence: `pytest` test signs a file, modifies a byte in the first document, runs verify-signature, asserts exit code 1 and failure message
  - Steps:
    - [ ] Add test in `tests/pid/test_verify.py`:
      - Modifying any byte of the first document after signing causes verification to fail with exit code 1

- [ ] **Task 3.3: `verify-signature` rejects unsigned files**
  - TaskType: OUTCOME
  - Entrypoint: `i2code pid verify-signature path/to/pid.yaml` (file with no second YAML document)
  - Observable: Exit code `1`, stdout prints `pid.yaml: unsigned file — no signature document found`
  - Evidence: `pytest` test creates an unsigned `pid.yaml`, runs verify-signature, asserts exit code 1 and unsigned file message
  - Steps:
    - [ ] Add test in `tests/pid/test_verify.py`:
      - Unsigned file (no `---` separator) returns exit code 1 with unsigned file message

- [ ] **Task 3.4: `verify-signature` reports missing public key**
  - TaskType: OUTCOME
  - Entrypoint: `i2code pid verify-signature path/to/pid.yaml` (with `PID_VERIFY_KEY_<key_id>` not set)
  - Observable: Exit code `1`, stdout prints `pid.yaml: public key not found — set PID_VERIFY_KEY_<key_id> environment variable`
  - Evidence: `pytest` test signs a file, unsets the verify key env var, runs verify-signature, asserts exit code 1 and missing key message
  - Steps:
    - [ ] Add test in `tests/pid/test_verify.py`:
      - Missing public key env var returns exit code 1 with actionable error message including the expected env var name

- [ ] **Task 3.5: `verify-signature` rejects unsupported algorithms**
  - TaskType: OUTCOME
  - Entrypoint: `i2code pid verify-signature path/to/pid.yaml` (with `signature.algorithm` set to something other than `Ed25519`)
  - Observable: Exit code `1`, stdout prints `pid.yaml: unknown algorithm 'RSA-SHA256' (supported: Ed25519)`
  - Evidence: `pytest` test creates a `pid.yaml` with a hand-crafted signature document using `algorithm: RSA-SHA256`, runs verify-signature, asserts exit code 1 and unsupported algorithm message
  - Steps:
    - [ ] Add test in `tests/pid/test_verify.py`:
      - Unsupported algorithm in signature document returns exit code 1 with error listing supported algorithms

---

## Steel Thread 4: Full End-to-End Workflow

This thread validates the complete first-time setup workflow from the spec (Scenario 1) as a single integration test.

- [ ] **Task 4.1: Full keygen → sign → verify workflow succeeds end-to-end**
  - TaskType: OUTCOME
  - Entrypoint: Sequence: `i2code pid keygen` → `source env.sh` → `i2code pid sign` → `i2code pid verify-signature`
  - Observable: Each command succeeds, final verify-signature exits 0 with valid signature message
  - Evidence: `pytest` integration test runs the complete workflow: generates keys, signs a `pid.yaml`, verifies the signature; `test-scripts/test-pid-sign-verify.sh` already covers CLI-level end-to-end
  - Steps:
    - [ ] Create `tests/pid/test_workflow_integration.py` — full workflow test:
      - Generate key pair → load keys → sign `pid.yaml` → verify signature → assert success
      - Generate key pair → sign → modify content → verify → assert failure (tampering detection)
    - [ ] Verify `test-scripts/test-end-to-end.sh` covers the full workflow
