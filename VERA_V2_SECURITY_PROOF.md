# VERA v2 — Informal Security Proof

## Theorem 1: Plaintext Confinement

Plaintext listening events exist only inside the TEE enclave.

Proof:
- HPKE is IND-CCA secure (RFC 9180)
- sk_tee sealed in TEE hardware
- Client verifies attestation
- Network path blind (ciphertext only)
- Conclusion: Plaintext in TEE only

## Theorem 2: Anti-Replay (Triple Defense)

Attacker cannot replay valid ciphertext.

Proof:
- Counter monotonic per client (persistent)
- Timestamp monotonic (server checks)
- Exact nonce unique (server cache)
- Conclusion: Replay infeasible

## Theorem 3: Attestation Binding

Client encryption bound to verified TEE.

Proof:
- quote.reportdata = SHA256(pk_tee || nonce || version || measurement)
- Client verifies DCAP signature
- Client verifies binding
- Conclusion: No downgrade possible
