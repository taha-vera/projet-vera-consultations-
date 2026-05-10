# ANCRE
## Attested Noise Client Runtime Engine
### Technical Whitepaper — v0.2

*Version 0.2 — May 2026*
*SAS VERA — Paris, France*
*Repository: github.com/taha-vera/ancre-protocole*
*Contact: tahahouari@hotmail.fr*

---

# Section 1 — Introduction

## 1.1 Problem Statement

VERA Radio provides differential privacy guarantees for audio listening signals at the middleware layer. Its security model is explicit: individual-level protection is bounded by formal DP guarantees, the audit chain is cryptographically verifiable, and the aggregation pipeline is open and reproducible.

One boundary remains deliberately unaddressed in VERA Radio: **client-side noise injection is not attestable**. VERA assumes that the platform operator deploys the client SDK honestly. This assumption is contractually enforced and audit-detectable post-hoc — but it is not cryptographically proven at the moment of signal submission.

For sectors where regulatory requirements demand stronger guarantees — healthcare data (HDS), financial behavioral analytics (DSP2, DORA), critical infrastructure (NIS2) — a contractual assumption is insufficient. What is required is a hardware-rooted attestation that the noise injection occurred on a certified device, at the declared parameters, before transmission.

ANCRE addresses this requirement.

## 1.2 ANCRE's Approach

ANCRE (Attested Noise Client Runtime Engine) extends the VERA Radio pipeline with a hardware attestation layer based on the GSMA IoT SAFE standard. The SIM card — a Secure Element certified Common Criteria EAL4+/5+, present on every phone, independent of any GAFA infrastructure — signs a commitment over the noisy signal and the attestation metadata before any data leaves the device.

The server verifies this attestation before accepting any signal into the aggregation buffer. Signals without valid SIM attestation are rejected at the perimeter.

ANCRE does not solve every privacy problem. Specifically, it does not cryptographically prove that Laplace noise with ε=1.0 was applied — this remains an architectural limitation documented in Section 4. What it does prove is that a SIM-resident key, whose certificate chains to a trusted telecom operator PKI, signed the declared noisy signal value with the declared metadata. This is a significantly stronger guarantee than software-only attestation.

## 1.3 Red Team Validation

Prior to v0.2, ANCRE v0.1 was subjected to a multi-AI red team exercise involving six independent security reviewers: DeepSeek, GPT-4o, Mistral, a fourth independent reviewer, Mythos, and Perplexity. The review identified 12 exploitable vulnerabilities across cryptographic, implementation, and privacy domains.

All critical findings were addressed in v0.2. The red team process and its findings are documented in Section 4 (Security Model) and Appendix A (Red Team Summary).

## 1.4 Scope of This Document

- **Section 2** — Architecture and components
- **Section 3** — Technical pipeline: attestation, verification, aggregation
- **Section 4** — Threat model, red team findings, and patch summary
- **Appendix A** — Red team finding matrix

---

# Section 2 — Architecture

## 2.1 Design Principles

ANCRE inherits all four VERA Radio design principles and adds a fifth:

1. **Privacy by destruction** — raw signal destroyed before transmission
2. **Role separation** — client, aggregator, and B2B buyer share no inputs
3. **Auditability without raw access** — compliance verifiable without individual data
4. **Invariant enforcement** — ε_total, K, wK are hard invariants with kill-switches
5. **Hardware-rooted attestation** — SIM signs the noisy signal; server verifies before aggregation

## 2.2 System Components

```
┌───────────────────────────────────────────────────────┐
│                    USER DEVICE                         │
│                                                       │
│  ┌────────────┐   ┌──────────────────────────────┐   │
│  │ Raw signal │──▶│    ANCRE Client Runtime        │   │
│  └────────────┘   │                              │   │
│                   │  1. validate_signal([0,1])   │   │
│                   │  2. inject Laplace (ε=1.0)   │   │
│                   │  3. destroy raw signal        │   │
│                   │  4. build SignedPayload:      │   │
│                   │     - canonical_hash(noisy)  │   │
│                   │     - server nonce            │   │
│                   │     - slot, sim_mode          │   │
│                   │     - timestamp_utc           │   │
│                   │  5. SIM signs payload bytes   │   │
│                   └──────────────┬───────────────┘   │
│                                  │                    │
│            ┌─────────────────────▼─────────────────┐ │
│            │        SIM — IoT SAFE Applet           │ │
│            │  Ed25519 key (never exported)          │ │
│            │  Signs: SHA256(JSON(payload))          │ │
│            │  CC EAL4+/5+ — operator PKI cert       │ │
│            └─────────────────────────────────────────┘ │
└──────────────────────────────┬────────────────────────┘
                               │ AncreAttestation:
                               │  noisy_value + SignedPayload
                               │  + payload_signature + cert_chain
                               ▼
┌───────────────────────────────────────────────────────┐
│              ANCRE AGGREGATION SERVER                  │
│                                                       │
│  AncreVerifierV2:                                     │
│   1. Payload size guard (≤8KB cert)                   │
│   2. validate_signal (NaN/Inf/bounds)                 │
│   3. MOCK rejection if production                     │
│   4. Timestamp freshness (±5min window)               │
│   5. Nonce anti-replay (UUID cache)                   │
│   6. Canonical hash check (struct.pack IEEE754)       │
│   7. Cert parse + expiry check                        │
│   8. Operator org check (trusted_operator_orgs)       │
│   9. CA chain validation (if configured)              │
│  10. Device quota check (cert serial counter)         │
│  11. Ed25519 verify (try/except — no crash)           │
│                                                       │
│  AncreServerV2:                                       │
│   - Buffer limit (10,000 signals max)                 │
│   - Buffer timeout (1h flush)                         │
│   - Coalition cap by device identity (wK=0.3)         │
│   - TMoM aggregation                                  │
│   - Server noise scale = 1/k_actual / ε_server        │
│   - Kill-switch: K<100 or ε_total>1.5                │
│   - Ed25519 sign + RFC3161 anchor                     │
└───────────────────────────────────────────────────────┘
```

## 2.3 GSMA IoT SAFE

The SIM attestation layer is based on GSMA IoT SAFE (SIM Applet For Secure End-to-End Communication), an open standard that enables cryptographic operations inside the SIM without exposing the private key. The key is generated on-card and cannot be exported.

ANCRE uses Ed25519 as the signature algorithm (algorithm identifier 0x09 in the IoT SAFE applet). The SIM signs `SHA256(JSON(payload))` where the payload is a deterministic JSON serialization of: signal hash, server nonce, slot, sim_mode, and timestamp.

In v0.2, all five fields are signed. In v0.1, only the signal hash was signed — leaving slot, sim_mode, and timestamp unauthenticated and swappable.

## 2.4 Operator PKI Independence

ANCRE's trust root is the telecom operator's PKI, not Google, Apple, or any GAFA infrastructure. The SIM certificate chains to the operator's CA, which issues certificates only to genuine IoT SAFE-provisioned SIMs.

Target operators: Orange (IoT SAFE declared 2021), SFR, Bouygues Telecom, Transatel (MVNO, faster onboarding). The operator relationship is a B2B partnership, not a technical dependency — ANCRE can switch operators by updating its trusted CA list.

---

# Section 3 — Technical Pipeline

## 3.1 Signal Canonicalization

**v0.1 flaw:** `str(float)` serialization is non-deterministic across Python versions and locales.

**v0.2 fix:** All signal hashing uses IEEE 754 big-endian binary encoding:

```python
def canonical_signal_bytes(signal: float) -> bytes:
    return struct.pack('>d', signal)

def canonical_signal_hash(signal: float) -> bytes:
    return hashlib.sha256(canonical_signal_bytes(signal)).digest()
```

This produces exactly 8 bytes, identical across all platforms, for any given float64 value.

## 3.2 SignedPayload

The SIM signs a canonical JSON serialization of five fields:

```json
{
  "nonce": "<UUID issued by server>",
  "signal_hash": "<base64(sha256(struct.pack('>d', signal)))>",
  "sim_mode": "IOTSAFE",
  "slot": 1,
  "timestamp_utc": "<ISO 8601>"
}
```

`sort_keys=True, separators=(',', ':')` ensures deterministic byte ordering across implementations.

The server nonce is issued per-request, preventing replay attacks regardless of signal value.

## 3.3 Server Verification (AncreVerifierV2)

Verification proceeds in strict order, failing fast on any violation:

| Step | Check | Patch |
|---|---|---|
| 1 | Cert size ≤ 8KB | P7 |
| 2 | NaN/Inf/bounds guard | P4 |
| 3 | MOCK rejection | P8 |
| 4 | Timestamp freshness (±5min) | P2 |
| 5 | Nonce not in used cache | P2 |
| 6 | Canonical hash match (hmac.compare_digest) | P3 |
| 7 | Cert parse + expiry | P1 |
| 8 | Operator org in trusted list | P1 |
| 9 | CA chain validation | P1 |
| 10 | Device quota (cert serial counter) | P5 |
| 11 | Ed25519 verify (try/except) | P6 |

All steps are wrapped in try/except. No step can raise an unhandled exception.

## 3.4 Coalition Cap (v0.2)

**v0.1 flaw:** Coalition cap based on outlier deviation heuristic — evadable by coordinated signals near the median.

**v0.2 fix:** Coalition cap based on device identity (cert serial number):

```python
max_per_device = int(k_actual * W_K)  # = 30% of buffer
for noisy_val, serial in self._buffer:
    if device_included.get(serial, 0) < max_per_device:
        filtered.append(noisy_val)
        device_included[serial] += 1
```

A single device (SIM) can contribute at most `floor(K * 0.3)` signals regardless of their values. This is a cryptographic bound, not a statistical heuristic.

## 3.5 Server-Side Noise (v0.2)

**v0.1 flaw:** Noise scale fixed to `1/K_MIN` regardless of actual buffer size.

**v0.2 fix:** Noise scale calibrated to actual contributing population:

```python
sensitivity = 1.0 / k_filtered   # actual sensitivity
noise_scale = sensitivity / EPSILON_SERVER
aggregate += np.random.laplace(0.0, noise_scale)
```

For k_filtered=150, noise_scale = 1/150/0.5 = 0.0133, which is smaller (tighter) than the v0.1 fixed scale of 1/100/0.5 = 0.02. This improves utility while maintaining the ε_server=0.5 guarantee.

---

# Section 4 — Threat Model and Red Team Summary

## 4.1 Governing Principle

> **ANCRE reduces systemic centralized risk and provides hardware-rooted attestation of signal origin. It does not prove that differential privacy noise was applied at the declared parameters.**

This distinction is the most important architectural fact about ANCRE. It is not a gap — it is an explicit, documented boundary.

## 4.2 What ANCRE Proves

A valid ANCRE attestation proves:

- A SIM-resident Ed25519 key signed the declared noisy signal value
- The signing key's certificate chains to a trusted telecom operator PKI
- The certificate was valid at the time of signing
- The nonce had not been used before (freshness)
- The signal value is within [0,1] and is not NaN or Inf
- The device has not exceeded its per-session signal quota (Sybil resistance)
- The sim_mode field was set at signing time (not tampered post-signature)

## 4.3 What ANCRE Does Not Prove

- That Laplace noise with ε=1.0 was applied to a raw signal
- That the noisy value was not crafted by the operator to bias the aggregate
- That the SIM hardware was not physically compromised
- That the telecom operator's PKI was not compromised

These limitations are documented in the SLA and threat model. A malicious B2B operator who controls the client binary can still submit arbitrary values. ANCRE detects Sybil attacks and replay attacks; it does not detect a single honest-looking but strategically chosen value.

## 4.4 Red Team Findings — v0.1 → v0.2

| ID | Finding | Severity | Status v0.2 |
|---|---|---|---|
| C1 | PKI bypass via self-signed cert | Critical | ✅ CA validation added |
| C2 | Anti-replay absent | Critical | ✅ Nonce + timestamp window |
| C3 | Float hash non-deterministic | Critical | ✅ struct.pack IEEE754 |
| C4 | NaN/Inf injection | High | ✅ validate_signal guard |
| C5 | sim_mode unauthenticated | High | ✅ sim_mode in SignedPayload |
| C6 | Coalition cap evadable (outlier heuristic) | High | ✅ Identity-based cap |
| C7 | Kill-switch static (never triggers) | High | ⚠️ Documented limitation |
| C8 | Exception on verify() → DoS | High | ✅ try/except all steps |
| C9 | Noise scale K_MIN vs k_actual | Medium | ✅ k_actual calibration |
| C10 | K counts signals not users | High | ✅ Device quota tracking |
| C11 | Buffer unbounded | Medium | ✅ 10,000 limit + timeout |
| C12 | DP client unenforced | Architectural | ⚠️ Documented limitation |

**⚠️ C7 — Kill-switch static:** The `EPSILON_TOTAL` constant check is a configuration guard, not a runtime privacy accountant. True per-user composition accounting requires persistent identity, which contradicts ANCRE's architecture. This limitation is documented and will be addressed in v0.3 via session-scoped budget tracking without persistent identity.

**⚠️ C12 — DP client unenforced:** No cryptographic proof that Laplace noise was applied client-side is possible without ZK-proofs or TEE attestation. This is the fundamental limitation of software-layer DP. ANCRE reduces but does not eliminate this gap.

## 4.5 Non-Goals

1. Proof of correct noise distribution at the client
2. Protection against a fully compromised client binary
3. Anonymization of metadata external to the signal (IP, device fingerprint)
4. Perfect forward secrecy for pre-ANCRE data
5. Hardware attestation on iOS (Apple blocks third-party SIM access)

---

# Appendix A — Red Team Reviewer Matrix

| Reviewer | Platform | Finding quality | Key unique contribution |
|---|---|---|---|
| Reviewer #1 | Independent | ★★★★★ | Sybil device ID, sensitivity TMoM, PKI PoC |
| Reviewer #2 | Independent | ★★★★★ | Metadata not signed, exception DoS |
| Reviewer #3 | Mistral | ★★★★ | Timestamp client-side, kill-switch static |
| Reviewer #4 | Independent | ★★★★ | NaN/Inf, adaptive DP composition |
| Reviewer #5 | Mythos | ★★★ | Confirmation, base64 analysis |
| Reviewer #6 | Perplexity/GPT | ★★ | Duplicate of Reviewer #2 |
| Meta (Llama) | Meta | — | Refused (over-refusal) |

All 12 critical findings were identified by at least two independent reviewers. The consensus threshold (3+ reviewers) was reached for 8 of 12 findings.

---

*End of ANCRE Technical Whitepaper v0.2*
*Next: Section 5 — Formal Privacy Guarantees and SLA Thresholds*
