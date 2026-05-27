# VERA v1 → v2 Detailed Diff

## Architecture Changes

### CDN Layer

**v1 (Model B)**:
git add VERA_DIFF_V1_TO_V2.md
git commit -m "architecture: pipeline ASCII + detailed v1→v2 diff (crypto, collectors, keys, replay)"
git push

cat > VERA_DIFF_V1_TO_V2.md << 'END'
# VERA v1 → v2: Model B to Model A+ Transition

## Core Changes

### 1. Client Encryption (NEW)
v1: plaintext HTTPS POST
v2: HPKE-encrypted + Ed25519-signed

### 2. Nonce Management (NEW)
v1: random, no replay check
v2: counter || timestamp_ms || random (monotonic)

### 3. Attestation (MANDATORY)
v1: optional
v2: client MUST verify quote + mrenclave + binding

### 4. Signature (NEW)
v1: none
v2: Ed25519(entire_message) including nonce + keys

### 5. CDN/LB Role (CHANGED)
v1: active (inspect payload)
v2: blind passthrough (ciphertext only)

### 6. Collector Role (CHANGED)
v1: decrypts + logs plaintext
v2: blind forwarder (no inspection, metadata only)

### 7. Key Rotation (CHANGED)
v1: manual, rare
v2: automatic 24h + client enforces TTL

### 8. Plaintext Destruction (IMPROVED)
v1: del payload + gc (weak)
v2: triple-pass fill(0xAA) + fill(0x55) + zeroize() + lfence (Rust)

## Attack Surface Summary

| Attack | v1 | v2 |
|--------|----|----|
| External eavesdrop | ✅ Protected | ✅ Protected |
| CDN exfil | ❌ Vulnerable | ✅ Protected |
| LB mirroring | ❌ Vulnerable | ✅ Protected |
| Mesh tap | ❌ Vulnerable | ✅ Protected |
| Backend logging | ❌ Vulnerable | ✅ Protected |
| Replay | ❌ Vulnerable | ✅ Protected |
| Effort to break | Very low (10 lines) | Very high (break crypto) |

## Operational Impact

v1 → v2 requires:
- Client SDK: HPKE + Ed25519 + attestation verification
- Server: Dual-stack support (v1 + v2 parallel)
- TEE: Updated decryption + anti-replay logic
- Observability: Shift from payload logging to metadata only
- Ops: Key rotation automation + TTL enforcement

Effort: 7-8 months engineering + QA + migration

Ready for CCS/PETS review.
END

git add VERA_DIFF_V1_TO_V2.md
git commit -m "diff: v1→v2 Model B to A+ (crypto, CDN blind, replay protection)"
git push
git add VERA_DIFF_V1_TO_V2.md
git commit -m "diff: v1→v2 Model B to A+ (crypto, CDN blind, replay protection)"
git push
git log --oneline -5
git log --oneline -5
# Quitte le prompt et exécute :
git log --oneline -5
