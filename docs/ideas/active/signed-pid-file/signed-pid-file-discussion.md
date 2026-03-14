# Signed PID File - Discussion

## Context from Codebase Analysis

- `i2code` is a Click-based Python CLI with subcommands: plan, idea, spec, design, implement, improve, etc.
- `isolarium` is an external tool that runs code in isolated VMs/containers.
- `IsolateMode` in `i2code` builds `isolarium` commands, passing `--env-file` and `--type` flags.
- `pid.yaml` does not yet exist in the codebase — it's a new concept.
- No existing signing/verification code exists in the project.

## Questions and Answers

### Q1: What is the threat model?

**A:** AI agent safety — preventing an AI agent (e.g., Claude running inside `isolarium`) from modifying `pid.yaml` to escalate its own permissions (requesting more env vars, changing isolation scripts).

### Q2: Where does signature verification happen?

**A:** In `isolarium` itself — before launching the VM/container, `isolarium` verifies the signature. This is the strongest guarantee since it's outside the agent's control.

### Q3: Is isolarium part of this codebase?

**A:** Out of scope. This idea focuses only on the `i2code` side — the `i2code pid sign` and `i2code pid verify-signature` subcommands and the `pid.yaml` format with signature support. Verification enforcement in `isolarium` is a separate concern.

### Q4: Key management approach?

**A:** Asymmetric signing, following the JWT model. The private key (`PID_FILE_SIGNING_KEY`) is held by the human developer for signing. The public key is used by `isolarium` for verification. The agent never has access to the private key.

### Q5: Should pid.yaml use JWT instead of a custom signature format?

**A:** Custom YAML format — second YAML document with `algorithm`, `key_id`, `signature` fields. Human-readable and stays within YAML conventions. Will use JWS-style algorithm names (e.g., `RS256`) for familiarity.

### Q6: Canonical serialization?

**A:** Sign the raw bytes of the first YAML document as they appear in the file (up to the `---` separator). Simple and deterministic. Trade-off: re-formatting the file invalidates the signature, but this is acceptable — if the file changes for any reason, it should be re-signed.

### Q7: Algorithm choice?

**A:** Ed25519 only. Modern, fast, small keys. Python's `cryptography` library supports it. The `algorithm` field in the signature document will be set to `Ed25519` but initially only this algorithm is supported.

### Q8: Key format?

**A:** PEM-encoded Ed25519 private key in the `PID_FILE_SIGNING_KEY` env var. Standard format, compatible with `openssl` and Python's `cryptography` library.

### Q9: Key generation command?

**A:** Yes — `i2code pid keygen` will generate an Ed25519 key pair in PEM format.

### Q10: keygen output?

**A:** Write key files to a user-specified directory (e.g., `i2code pid keygen --output-dir <dir> --key-id <id>`). Generates:
- `<key_id>-private.pem` — Ed25519 private key
- `<key_id>-public.pem` — Ed25519 public key
- `<key_id>-env.sh` — bash script that exports `PID_FILE_SIGNING_KEY` and `PID_VERIFY_KEY_<key_id>` so the user can `source <key_id>-env.sh` to set up their environment.

### Q10a: Cross-language compatibility?

**Q:** Isolarium is written in Go — will Ed25519 verification be straightforward?
**A:** Yes. Go's `crypto/ed25519` is in the standard library with no external dependencies, and `encoding/pem` handles the key format. Ed25519 + PEM is a good cross-language choice for the Python/Go split.

### Q11: Public key distribution?

**A:** `key_id` maps to an env var on the verifier side (e.g., `key_id: "my-key"` → `PID_VERIFY_KEY_my-key`). The `i2code` side lets the user specify the `key_id` when signing. Resolution is `isolarium`'s concern.

### Q12: What should happen when verify-signature fails?

**A:** Exit with non-zero status and print an error message. Suitable for scripting and CI.

### Q13: verify-signature key source?

**A:** Looks up `PID_VERIFY_KEY_<key_id>` from environment variables or `.env.local`.

### Q14: Handling unsigned pid.yaml?

**A:** Treat as verification failure — unsigned files are rejected.

### Q15: sign command behavior when signature already exists?

**A:** Replace the existing signature — re-sign with the current key.

### Q16: Default key_id?

**A:** Required — `i2code pid sign --key-id <id> [path]`.

### Q17: Default path for pid.yaml?

**A:** Default to `./pid.yaml` in the current directory.

## Classification

**Type:** C — Platform/infrastructure capability

**Rationale:** This is a security mechanism for the i2code/isolarium platform. It provides signing and verification of `pid.yaml` configuration files to protect against AI agent privilege escalation. It's consumed by developers (via CLI) and by `isolarium` (via the file format), making it a platform capability rather than a user-facing feature.
