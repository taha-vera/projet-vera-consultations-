# 11. Design Model A+: CCS-Grade Ingestion Pipeline

## 11.1 Threat Model
- A_external, A_operator, A_timing, A_replay, A_tee_side

## 11.2 Cryptographic Bindings
TEE Identity Binding, Client Message Binding, HPKE Context Binding

## 11.3 Anti-Replay
Monotonic counter, timestamp, exact nonce verification

## 11.4 TEE Key Rotation
Server rotation every 24h, client enforces TTL

## 11.5 Plaintext Destruction (Rust)
zeroize triple-pass + lfence

## 11.6 Message Format
version, client_session_id, encapsulated_key, ciphertext, nonce, signature

## 11.8 Invariants
✅ Plaintext only in TEE (Rust)
✅ Attestation verified client-side
✅ HPKE AAD bound to TEE identity
✅ Anti-replay: counter + timestamp + nonce
✅ Quote binds to pk_tee
✅ TTL enforcement
✅ zeroize triple-pass

## 11.9 CCS Readiness
Ready for CCS submission.
