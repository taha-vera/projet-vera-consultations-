# ANCRE — Threat Model v1.3
## Formal Adversary Model for Whitepaper v1.3

**Version** : 1.3  
**Status** : Post-review consolidation (10 AI reviewers)  
**Date** : May 2026

---

## 0. Taxonomy of Claims

Every security claim in ANCRE carries an explicit status tag:

| Tag | Meaning | Acceptance criterion |
|---|---|---|
| **[PROVEN]** | Formal mathematical guarantee | Lemma + proof in paper |
| **[ARCHITECTURAL]** | Guaranteed by system design | Structural argument, no code trust |
| **[OPERATIONAL]** | Depends on deployment discipline | Documented policy, not enforced cryptographically |
| **[CONJECTURAL]** | Intuitive, no formal proof | Explicitly scoped, never used to support theorems |
| **[NOT CLAIMED]** | Explicitly out of scope | Named to prevent overclaiming |

**Rule**: If a claim has no tag, it is not a claim.

---

## 1. System Trust Boundary (Trusted Computing Base)

ANCRE assumes the following trusted components:

```
TRUSTED:
- Client-side signal validation (H2)
- IoT SAFE SIM PKI chain (operator CA)
- Rust cryptographic primitives (ChaCha20, SHA-256)
- RFC3161 timestamping (FreeTSA)

NOT TRUSTED (adversarial):
- Network between client and server
- Server operator (beyond H1/H2/H6 enforcement)
- Auditor (A3)
- Any external observer
```

**Explicit assumption**: ANCRE does NOT assume a Byzantine-fault-tolerant server. The server is assumed to follow the protocol (honest) but may be curious (A1). A fully malicious server (A0) is modeled separately with explicit non-coverage.

---

## 2. Adversary Definitions

### A0 — Active Malicious Server [NEW]

**Capacities**:
- Controls server code and pipeline
- Can modify ε, suppress DLap noise, reorder signals
- Can selectively disable kill-switch
- Can manipulate TMoM inputs before aggregation
- Can fabricate metadata (n, ε_used)

**Objective**: Extract individual signals or bias aggregates undetectably.

**ANCRE coverage**:
- [NOT CLAIMED] No formal defense against A0
- [ARCHITECTURAL] RFC3161 anchoring provides post-hoc auditability
- [OPERATIONAL] Open-source code + reproducible benchmarks allow external verification

**Explicit limitation**:
> "ANCRE does not provide cryptographic integrity guarantees against a fully malicious server. Resistance to A0 requires TEE deployment (planned v0.8) or verifiable computation."

---

### A1 — Honest-but-Curious Server

**Capacities**:
- Sees all raw signals before aggregation
- Knows n, ε, K, α
- Observes M(D) = aggregated output
- Has access to metadata (timestamps, device counts)

**Objective**: Infer x_k (individual signal value).

**ANCRE coverage**:
- [PROVEN] ε=0.5-DP under substitute adjacency (Theorem 1)
  → Pr[infer x_k] ≤ e^0.5 × Pr[baseline]
- [PROVEN] Exact DLap eliminates LSB leakage (δ=0)

**MIA target**: AUC < 0.53 (theoretical bound: e^0.5/(1+e^0.5) ≈ 0.622)

---

### A2 — Passive External Observer

**Capacities**:
- Observes only published M(D)
- Knows n, ε, K (public metadata)
- Accumulates up to 3 aggregates (k ≤ 3)
- May have auxiliary knowledge (public datasets)

**Objective**: Linkage attack, reconstruction of individual trends.

**ANCRE coverage**:
- [PROVEN] Bounded cumulative leakage under DP composition:
  ε_total = 1.5 over k=3 aggregations (Corollary 1)
- [ARCHITECTURAL] Kill-switch enforces hard budget limit
- [NOT CLAIMED] Longitudinal correlation beyond DP composition bounds

**Clarification**: DP composition bounds mathematical leakage. It does not bound exploitable temporal patterns with auxiliary data (→ see A8).

---

### A3 — Compromised Auditor

**Capacities**:
- Legitimate access to HMAC audit chain
- Holds shared HMAC key
- Can read all historical aggregates and metadata
- Sees: n, ε_used, timestamps, session identifiers

**Objective**: Session linkage, historical reconstruction, rollback.

**ANCRE coverage**:
- [ARCHITECTURAL] Append-only chain → rollback resistance only
- [OPERATIONAL] Hash expiration → reduces linkage window

**Explicit limitations** (required by all reviewers):
> "ANCRE currently does not provide cryptographic unlinkability against a fully compromised auditor holding historical HMAC keys."

**Blast radius analysis**:
- Single key compromise → full historical linkage possible
- Expiration window: reduces to last TTL period only
- Forward secrecy: NOT IMPLEMENTED in v0.7

**Key lifecycle (required for v0.8)**:
```
Current (v0.7): single shared key
Required (v0.8):
  - Per-epoch key derivation
  - Forward secrecy via key rotation
  - Blast radius: one epoch only
```

**What A3 CANNOT do**:
- Modify existing entries (append-only structure)
- Reconstruct raw signals (destroyed before aggregation, H6)
- Access signals from other sessions after key rotation (v0.8)

---

### A4 — Malicious Participant (Sybil)

**Capacities**:
- Controls j distinct physical SIMs
- Submits j signals per window
- Chooses signal values arbitrarily
- Can coordinate timing

**Objective**: Bias aggregate toward target value.

**ANCRE coverage**:
- [PROVEN] TMoM (α=0.1) — formal breakdown point: trim absorbs up to α=10% extremes
  → Sybil with j ≤ 0.1×n signals: NO EFFECT on trimmed set
  → Sybil with j > 0.1×n signals: bounded degradation
- [ARCHITECTURAL] max_per_device = 1 (server-enforced)
- [OPERATIONAL] IoT SAFE SIM cost ≈ EUR 5-50/SIM/year
  → 51 SIMs to dominate K=100 window ≈ EUR 255-2,550/year

**Reclassification from v1.2**:
- SIM cost: OPERATIONAL → **economic friction only, not a security guarantee**
  > "SIM cost is geography-dependent and state-actor-invariant. It constitutes friction, not defense."

**TMoM breakdown point**:
- j < 10%×n: full protection [PROVEN]
- j = 10-50%×n: degraded utility, DP guarantee maintained
- j > 50%×n: TMoM breakdown, DP guarantee on biased data

---

### A5 — Partial Collusion (A2 + A4)

**Capacities**:
- Submits controlled signals (A4 capability)
- Observes published M(D) (A2 capability)
- Correlates own inputs with output differences
- Can iterate up to 3 windows (budget limit)

**Objective**: Differential attack — infer individual signals by varying inputs.

**ANCRE coverage**:
- [ARCHITECTURAL] Composition + kill-switch limits iterations to 3
  → Differential attack bounded by budget exhaustion
- [PROVEN] TMoM sensitivity: |ΔM(D)| ≤ Δ/n_eff + DLap noise
  → Signal-to-noise ratio: Sybil effect << noise floor

**Reclassification from v1.2**:
- DP composition [PROVEN] → [ARCHITECTURAL] for A5
  > "DP composition is proven for independent adaptive queries on static data.
  > It does not formally cover active injection attacks (poisoning + reconstruction)."

---

### A6 — Temporal Observer

**Capacities**:
- Accumulates historical aggregates
- Has knowledge of evolving listening habits (public data)
- Can correlate old aggregates with current known behaviors

**Objective**: Temporal re-identification of individuals who changed habits.

**ANCRE coverage**:
- [PROVEN] Bounded cumulative leakage: ε_total = 1.5 (3 aggregations max)
- [ARCHITECTURAL] NAV raw data destruction
- [CONJECTURAL] VERA-D temporal degradation policy (see §3)

**Clarification**:
> "DP composition bounds mathematical leakage per aggregation window.
> It does not bound long-range temporal correlation exploitable with auxiliary datasets."

---

### A7 — Active Malicious Insider / Infrastructure [NEW]

**Capacities**:
- Root access to server infrastructure
- Can dump memory, logs, snapshots, HMAC keys
- Can observe system-level metadata: IP addresses, request sizes, timing
- Can correlate aggregates with network-layer activity

**Objective**: Extract pre-noise signals, bypass VERA-D via backup, timing correlation.

**ANCRE coverage**:
- [NOT CLAIMED] No formal defense against infrastructure-level adversary
- [OPERATIONAL] Separation of duties (platform ≠ auditor)
- [CONJECTURAL] TEE deployment (ARM TrustZone, v0.8 roadmap)

**Explicit limitation**:
> "ANCRE does not model infrastructure-level adversaries. Defense requires hardware isolation (TEE) which is planned for v0.8 but not implemented in v0.7."

---

### A8 — Side-Information Adversary [NEW]

**Capacities**:
- Holds large external datasets (Spotify, social media, geo data)
- Observes M(D) over time
- Performs membership inference with auxiliary correlation
- Can fingerprint behavioral patterns

**Objective**: Re-identification via correlation with external datasets.

**ANCRE coverage**:
- [PROVEN] ε-DP is precisely designed for side-information resistance
  → Formal guarantee holds regardless of adversary's auxiliary knowledge
- [ARCHITECTURAL] K_MIN = 100 provides k-anonymity baseline

**Key point**:
> "ε-DP provides formal resistance to auxiliary information attacks by design.
> This is the primary mathematical motivation for DP in ANCRE."

**Residual risk**:
- Temporal patterns beyond DP bounds (→ VERA-D scope)
- Behavioral fingerprinting at population level (→ [NOT CLAIMED])

---

## 3. VERA-D — Temporal Minimization Policy

**Classification**: [OPERATIONAL] + [CONJECTURAL]  
**Scope**: A6 only

**Correct formulation** (validated by reviewer consensus):
> "VERA-D is a defense-in-depth temporal minimization policy intended to reduce long-term aggregation exposure beyond formal DP guarantees."

**What VERA-D IS**:
- A data retention and noise augmentation schedule
- A governance mechanism reducing residual re-identification risk
- An operational policy explicitly beyond DP formal bounds

**What VERA-D IS NOT**:
- An extension of DP guarantees [NOT CLAIMED]
- A proof of unlinkability [NOT CLAIMED]
- A prevention of re-identification [NOT CLAIMED]
- A substitute for ε-DP [NOT CLAIMED]

**Schedule**:
```
FRESH   (0-30d)   → aggregate intact, ε_total = 0.5
LIGHT   (30-90d)  → +DLap noise, ε_effective = 0.6
STRONG  (90-180d) → +DLap noise, ε_effective = 1.0
INVALID (180d+)   → aggregate returns None
```

**Honest limitation**:
> "VERA-D repels temporal attacks but does not prevent them.
> An adversary who snapshots at day 0 retains the FRESH aggregate permanently.
> ε_total already spent cannot be recovered."

---

## 4. Threats Not Considered (Explicit)

The following threats are explicitly OUT OF SCOPE for ANCRE v0.7:

| Threat | Reason for exclusion |
|---|---|
| A0 Byzantine server | Requires TEE or verifiable computation (v0.8 roadmap) |
| A7 Infrastructure root | Requires hardware isolation |
| Physical attacks (cold boot, side-channel) | Hardware threat model |
| Legal coercion / subpoena | Policy/legal scope, not cryptographic |
| Supply chain / build compromise | DevOps security scope |
| Network active adversary (MITM) | Assumes TLS transport security |
| Client-side code tampering | Client trust model |
| Group privacy | Not addressed in current DP formulation |

**Standard assumption**:
> "ANCRE assumes secure transport (TLS), no physical access to servers,
> and no state-level coercion. These are documented assumptions, not oversights."

---

## 5. Revised Classification Matrix

| Mechanism | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 |
|---|---|---|---|---|---|---|---|---|
| ε=0.5-DP (Thm 1) | ✅P | ✅P | — | — | — | ✅P | — | ✅P |
| Composition (Cor 1) | — | ✅P | — | — | ✅A | ✅P | — | — |
| TMoM sensitivity | ✅P | — | — | ✅P | ✅P | — | — | — |
| DLap exact (δ=0) | ✅P | ✅P | — | — | ✅P | — | — | — |
| Kill-switch | — | ✅O | — | — | ✅O | ✅O | — | — |
| NAV raw destruction | ✅A | ✅A | ✅A | — | ✅A | ✅A | — | — |
| max_per_device | — | — | — | ✅A | ✅A | — | — | — |
| HMAC chain | — | — | ✅A* | — | — | — | — | — |
| SIM cost | — | — | — | ⚠️O | ⚠️O | — | — | — |
| Hash expiration | — | — | ✅O | — | — | — | — | — |
| K-anonymity (K≥100) | — | — | — | — | — | — | — | ✅A |
| VERA-D | — | — | — | — | — | ✅C | — | — |
| TEE (planned v0.8) | — | — | — | — | — | — | 🔲 | — |

**Legend**:
```
✅P = PROVEN       (formal guarantee)
✅A = ARCHITECTURAL (design guarantee)
✅O = OPERATIONAL  (deployment policy)
✅C = CONJECTURAL  (explicitly scoped)
⚠️O = OPERATIONAL  (friction only, not security guarantee)
✅A* = append-only → rollback resistance only, NOT unlinkability
🔲  = PLANNED (v0.8)
—   = not applicable
```

---

## 6. Key Reclassifications from v1.2

| Mechanism | v1.2 | v1.3 | Reason |
|---|---|---|---|
| A4 SIM cost | [OPERATIONAL] | [OPERATIONAL] ⚠️ friction | Not a security guarantee |
| A5 DP composition | [PROVEN] | [ARCHITECTURAL] | Not proven under active injection |
| Kill-switch | [ARCHITECTURAL] | [OPERATIONAL] | Manual trigger, not cryptographic |
| A3 HMAC append-only | [ARCHITECTURAL] | [ARCHITECTURAL]*rollback only | Unlinkability NOT claimed |
| VERA-D | [CONJECTURAL] | [OPERATIONAL]+[CONJECTURAL] | Retention policy + heuristic |

---

*v1.3 — Post 10-AI-review consolidation*  
*Key additions: A0, A7, A8, "Threats not considered", blast radius analysis, VERA-D repositioning*
