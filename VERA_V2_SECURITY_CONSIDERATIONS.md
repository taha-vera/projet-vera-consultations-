# VERA v2 — Security Considerations for CCS/PETS

## 1. Cryptographic Assumptions

### HPKE (RFC 9180)
- **Mode**: HPKE(DH=X25519, KDF=SHA256, AEAD=ChaCha20-Poly1305)
- **Assumption**: IND-CCA security holds
- **Failure case**: Breaks confidentiality of plaintext
- **Mitigation**: Use standardized, audited implementations (libsodium, rustls)

### Ed25519 Signatures
- **Assumption**: Existential unforgeability
- **Failure case**: Attacker forges client signature
- **Mitigation**: Signature scope covers entire message (version, keys, nonce, payload)

### SHA256 Hashing
- **Assumption**: Collision resistance, preimage resistance
- **Failure case**: Attacker forges binding (quote, nonce, ledger)
- **Mitigation**: Use 256-bit hash (NIST standard)

---

## 2. Threat Model Scope

### In Scope (VERA v2 Protects Against)

**A_external**: Network eavesdropper
- Cannot decrypt HPKE ciphertext
- Cannot forge signatures (no sk_client)
- Cannot replay (nonce uniqueness)

**A_operator**: CDN/LB/collector/mesh admin
- Cannot see plaintext (encrypted end-to-end)
- Cannot modify messages (signature integrity)
- Cannot extract credentials (TEE isolation)

**A_replay**: Attacker with captured ciphertext
- Cannot replay (monotonic counter prevents)
- Cannot reuse across clients (session_id in nonce)
- Cannot reboot-replay (ledger persisted to disk)

**A_downgrade**: Attacker attempting protocol downgrade
- Cannot use v1 protocol (v2 validation mandatory)
- Cannot mix v1+v2 (version in signature)
- Cannot forge old quote (DCAP signature required)

### Out of Scope (VERA v2 Does Not Address)

**A_tee_sideChannel**: TEE microarchitecture attacks
- Spectre, Meltdown, LVI, Prime+Probe
- **Mitigation**: CPU microcode updates (Intel/AMD responsibility)
- **Risk level**: Low (requires physical access or shared CPU)

**A_supplyChain**: Compromised hardware/firmware
- Malicious enclave binary, BIOS backdoor
- **Mitigation**: Measurement verification, secure boot
- **Risk level**: Organization-specific

**A_clientCompromised**: User device fully compromised
- Keylogger, malware, rootkit
- **Mitigation**: Client-side security (device hardening)
- **Risk level**: Out of VERA scope

---

## 3. Implementation Security

### Cryptographic Operations

**Private Key Management**:
- sk_client: Ephemeral, generated per session, never persisted
- sk_tee: Sealed in TEE, never leaves enclave, rotated every 24h

**Plaintext Destruction**:
- Triple-overwrite: fill(0xAA), fill(0x55), zeroize()
- Memory fence: _mm_lfence() to prevent reordering
- Rust ownership: Compiler ensures no accidental copies

**Timing Attacks**:
- Signature verification: Use libsodium (constant-time)
- Comparison operations: Use constant-time crypto libraries
- Nonce lookup: HashMap (not timing-safe, but acceptable for cache hits)

### Anti-Replay Implementation

**Ledger Persistence**:
- JSON append-only to disk
- Hash chaining: entry_hash = SHA256(prev_hash || nonce || counter || timestamp)
- Rollback detection: Counter monotonically increasing

**Nonce Cache**:
- In-memory HashMap (fast lookup)
- TTL: 1 hour (aggressive cleanup)
- Reboot-replay: Ledger loaded from disk

---

## 4. Attestation Security

### DCAP Verification

**Steps**:
1. Extract quote from attestation report
2. Verify DCAP signature (Intel/AMD ECDSA)
3. Extract reportdata from quote
4. Verify reportdata = SHA256(pk_tee || nonce || version || measurement)

**Failure modes**:
- Invalid DCAP signature → reject (quote is forged)
- Reportdata mismatch → reject (quote not bound to this pk_tee)
- Expired quote (>5 min) → reject (replay from old attestation)

### Measurement Verification

**Steps**:
1. Compute mrenclave hash of TEE binary
2. Compare against known-good value from GitHub releases
3. Reject if mismatch (wrong enclave, compromised binary)

**Failure modes**:
- Unknown measurement → reject (attacker's TEE)
- Downgraded measurement → reject (v1 instead of v2)

---

## 5. Protocol Composition

### Message Integrity

**Signature scope**:
