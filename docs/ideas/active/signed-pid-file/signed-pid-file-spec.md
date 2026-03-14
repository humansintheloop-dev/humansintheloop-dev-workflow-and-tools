# Signed PID File — Platform Capability Specification

## Classification

**Type:** Platform/infrastructure capability

**Rationale:** This feature adds a security mechanism to the i2code/isolarium platform — digital signatures for `pid.yaml` configuration files. It protects the integrity of isolation configuration against tampering by AI agents running inside isolated environments.

## Purpose and Context

`pid.yaml` is a project-level configuration file that defines how `isolarium` sets up isolated environments (VMs/containers). It specifies isolation scripts to run and environment variables to inject — including secrets like `CS_ACCESS_TOKEN`.

An AI agent running inside an `isolarium` environment could modify `pid.yaml` to escalate its permissions: requesting additional environment variables, changing isolation scripts, or altering the isolation configuration. Digital signatures on `pid.yaml` allow `isolarium` to detect such tampering and refuse to launch with a modified configuration.

This specification covers the `i2code` side: CLI commands for key generation, signing, and signature verification. Enforcement of signature verification within `isolarium` (written in Go) is a separate concern.

## Threat Model

**Threat:** An AI agent running inside an `isolarium` VM/container modifies `pid.yaml` to escalate its own permissions.

**Mitigation:** The human developer signs `pid.yaml` with a private key that is never exposed to the agent. Before launching an environment, the verifier checks the signature using the corresponding public key. A missing or invalid signature causes rejection.

**Trust boundary:** The private signing key exists only on the host side (in `.env.local` or environment variables). The agent inside the VM never has access to it.

## Consumers

| Consumer | Role | Usage |
|---|---|---|
| Human developer | Signs `pid.yaml` after authoring or modifying it | Uses `i2code pid sign` and `i2code pid keygen` |
| Human developer / CI | Verifies `pid.yaml` signature for testing or validation | Uses `i2code pid verify-signature` |
| `isolarium` (Go, separate project) | Enforces signature verification before launching environments | Reads the signed `pid.yaml` format (out of scope for this spec) |

## Capabilities and Behaviors

### Capability 1: Key Generation (`i2code pid keygen`)

Generates an Ed25519 key pair and a convenience shell script for environment setup.

**Command:**
```
i2code pid keygen --key-id <id> --output-dir <dir>
```

**Arguments:**
- `--key-id` (required): Identifier for the key pair. Used as a file prefix and referenced in the signature's `key_id` field.
- `--output-dir` (required): Directory to write the generated files.

**Output files:**
- `<key_id>-private.pem` — PEM-encoded Ed25519 private key
- `<key_id>-public.pem` — PEM-encoded Ed25519 public key
- `<key_id>-env.sh` — Bash script that exports:
  - `PID_FILE_SIGNING_KEY` — contents of (or path to) the private key
  - `PID_VERIFY_KEY_<key_id>` — contents of (or path to) the public key

**Behavior:**
- Creates the output directory if it does not exist.
- Fails with an error if any of the output files already exist (prevents accidental key overwrite).
- Sets file permissions on `<key_id>-private.pem` to `0600` (owner read/write only).

### Capability 2: Signing (`i2code pid sign`)

Signs a `pid.yaml` file by appending a second YAML document containing the signature.

**Command:**
```
i2code pid sign --key-id <id> [path]
```

**Arguments:**
- `--key-id` (required): Identifier for the signing key. Written into the signature document's `key_id` field. The private key is read from the `PID_FILE_SIGNING_KEY` environment variable.
- `path` (optional): Path to the `pid.yaml` file. Defaults to `./pid.yaml`.

**Signing process:**
1. Read the file contents.
2. Extract the raw bytes of the first YAML document (everything before the first `---` document separator, or the entire file if no separator exists).
3. If a second YAML document (signature) already exists, strip it — only the first document's raw bytes are retained.
4. Load the private key from `PID_FILE_SIGNING_KEY` environment variable (PEM-encoded Ed25519 private key).
5. Sign the raw bytes using Ed25519.
6. Write the file back: first document bytes, followed by `\n---\n`, followed by the signature YAML document.

**Signed file format:**
```yaml
isolarium:
  vm:
    isolation_scripts:
      - path: scripts/vm/install-go.sh
---
signature:
  algorithm: Ed25519
  key_id: my-key
  value: <base64-encoded-signature>
```

**Error conditions:**
- `PID_FILE_SIGNING_KEY` environment variable is not set → error with message.
- `PID_FILE_SIGNING_KEY` does not contain a valid PEM-encoded Ed25519 private key → error with message.
- File at `path` does not exist → error with message.
- File at `path` does not contain valid YAML → error with message.

### Capability 3: Signature Verification (`i2code pid verify-signature`)

Verifies the digital signature on a `pid.yaml` file.

**Command:**
```
i2code pid verify-signature [path]
```

**Arguments:**
- `path` (optional): Path to the `pid.yaml` file. Defaults to `./pid.yaml`.

**Verification process:**
1. Read the file contents.
2. Split on the `---` document separator.
3. If no second document exists → verification failure ("unsigned file").
4. Parse the second document as YAML and extract `signature.algorithm`, `signature.key_id`, and `signature.value`.
5. Verify that `algorithm` is `Ed25519` → error if unsupported algorithm.
6. Look up the public key from `PID_VERIFY_KEY_<key_id>` environment variable (PEM-encoded Ed25519 public key).
7. Verify the signature against the raw bytes of the first document.
8. Print result and exit.

**Exit codes:**
- `0` — signature is valid.
- `1` — verification failed (invalid signature, unsigned file, missing key, unsupported algorithm).

**Output on success:**
```
pid.yaml: signature valid (key_id: my-key, algorithm: Ed25519)
```

**Output on failure (examples):**
```
pid.yaml: signature verification failed
pid.yaml: unsigned file — no signature document found
pid.yaml: unknown algorithm 'RSA-SHA256' (supported: Ed25519)
pid.yaml: public key not found — set PID_VERIFY_KEY_my-key environment variable
```

## File Format

### Unsigned `pid.yaml`

A single YAML document containing the `isolarium` configuration:

```yaml
isolarium:
  container:
    isolation_scripts:
      - path: scripts/container/install-go.sh
      - path: scripts/container/install-codescene.sh
        env:
          - CS_ACCESS_TOKEN
  vm:
    isolation_scripts:
      - path: scripts/vm/install-go.sh
```

### Signed `pid.yaml`

Two YAML documents in the same file, separated by `---`:

```yaml
isolarium:
  container:
    isolation_scripts:
      - path: scripts/container/install-go.sh
      - path: scripts/container/install-codescene.sh
        env:
          - CS_ACCESS_TOKEN
  vm:
    isolation_scripts:
      - path: scripts/vm/install-go.sh
---
signature:
  algorithm: Ed25519
  key_id: my-key
  value: YWJjZGVmZzEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkw
```

### Signature Document Fields

| Field | Type | Description |
|---|---|---|
| `signature.algorithm` | string | Signing algorithm. Currently only `Ed25519` is supported. |
| `signature.key_id` | string | Identifier for the public key used to verify the signature. Maps to `PID_VERIFY_KEY_<key_id>` env var. |
| `signature.value` | string | Base64-encoded Ed25519 signature of the first document's raw bytes. |

## Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `PID_FILE_SIGNING_KEY` | `i2code pid sign` | PEM-encoded Ed25519 private key for signing. |
| `PID_VERIFY_KEY_<key_id>` | `i2code pid verify-signature`, `isolarium` | PEM-encoded Ed25519 public key for verification. `<key_id>` matches the `key_id` in the signature document. |

These variables can be set directly in the environment or via `.env.local`.

## CLI Structure

The three commands are grouped under a new `i2code pid` subcommand group:

```
i2code pid keygen --key-id <id> --output-dir <dir>
i2code pid sign --key-id <id> [path]
i2code pid verify-signature [path]
```

This follows the existing `i2code` CLI pattern (Click-based, subcommand groups registered in `cli.py`).

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Dependencies** | Python `cryptography` library (already widely used; provides Ed25519 support) |
| **Cross-language compatibility** | PEM key format and Ed25519 signatures must be verifiable by Go's `crypto/ed25519` and `encoding/pem` standard library packages |
| **Performance** | All operations complete in under 1 second for typical `pid.yaml` files |
| **Key safety** | Private key file permissions set to `0600`. Private key never written to `pid.yaml` or stdout during normal operation |
| **Idempotency** | Running `sign` twice on the same file with the same key produces a valid signed file (replaces existing signature) |

## Scenarios and Workflows

### Scenario 1: First-Time Setup (Primary End-to-End Scenario)

A developer sets up signing for a project for the first time.

1. Developer runs `i2code pid keygen --key-id dev-signing --output-dir ~/.config/i2code/keys/`.
2. Three files are created: `dev-signing-private.pem`, `dev-signing-public.pem`, `dev-signing-env.sh`.
3. Developer runs `source ~/.config/i2code/keys/dev-signing-env.sh` to load keys into environment.
4. Developer runs `i2code pid sign --key-id dev-signing` in the project root.
5. `pid.yaml` is updated with a signature document appended after `---`.
6. Developer runs `i2code pid verify-signature` to confirm the signature is valid.
7. Output: `pid.yaml: signature valid (key_id: dev-signing, algorithm: Ed25519)`

### Scenario 2: Re-Signing After Configuration Change

A developer modifies `pid.yaml` (adds a new env var) and re-signs.

1. Developer edits the first document of `pid.yaml`.
2. Developer runs `i2code pid sign --key-id dev-signing`.
3. The existing signature is replaced with a new one covering the updated content.
4. Developer runs `i2code pid verify-signature` to confirm.

### Scenario 3: Detecting Tampering

An AI agent modifies `pid.yaml` inside the isolated environment.

1. Agent adds `SECRET_KEY` to the env list in `pid.yaml`.
2. `i2code pid verify-signature` (or `isolarium`'s built-in check) detects the signature is invalid.
3. Output: `pid.yaml: signature verification failed`
4. Exit code: `1`.

### Scenario 4: Unsigned File Rejection

A project has a `pid.yaml` without a signature.

1. Developer runs `i2code pid verify-signature`.
2. Output: `pid.yaml: unsigned file — no signature document found`
3. Exit code: `1`.

### Scenario 5: Missing Public Key

Verification is attempted but the public key env var is not set.

1. Developer runs `i2code pid verify-signature`.
2. The signature document specifies `key_id: prod-key`.
3. `PID_VERIFY_KEY_prod-key` is not set in the environment.
4. Output: `pid.yaml: public key not found — set PID_VERIFY_KEY_prod-key environment variable`
5. Exit code: `1`.

### Scenario 6: Key File Overwrite Protection

Developer accidentally runs `keygen` with an existing key ID.

1. Developer runs `i2code pid keygen --key-id dev-signing --output-dir ~/.config/i2code/keys/`.
2. `dev-signing-private.pem` already exists.
3. Command fails with error: file already exists.
4. No files are overwritten.

## Constraints and Assumptions

- **Python `cryptography` library** is used for Ed25519 operations. This must be added as a project dependency if not already present.
- **Only Ed25519** is supported initially. The `algorithm` field exists for future extensibility but the implementation rejects any value other than `Ed25519`.
- **Raw bytes signing** — the signature covers the exact bytes of the first YAML document as they appear in the file. Any formatting change (whitespace, key reordering, comment changes) invalidates the signature and requires re-signing.
- **No key rotation mechanism** — key rotation is handled manually by generating a new key pair and re-signing. The `key_id` field allows multiple keys to coexist.
- **`isolarium` verification is out of scope** — this spec covers only the `i2code` CLI commands. `isolarium` will consume the same file format and env var conventions but its implementation is separate.

## Acceptance Criteria

1. `i2code pid keygen --key-id <id> --output-dir <dir>` generates a valid Ed25519 key pair and env script.
2. `i2code pid sign --key-id <id>` produces a signed `pid.yaml` with a valid Ed25519 signature.
3. `i2code pid verify-signature` returns exit code `0` for a validly signed file and `1` for any failure case.
4. A `pid.yaml` signed by `i2code` (Python) can be verified using Go's `crypto/ed25519` with the generated public key.
5. Modifying any byte of the first YAML document after signing causes verification to fail.
6. Re-signing an already-signed file replaces the signature and produces a valid result.
7. Unsigned files are rejected by `verify-signature`.
8. `keygen` refuses to overwrite existing key files.
9. All error conditions produce clear, actionable error messages and non-zero exit codes.
