# VERA Security Model
### Section 4 — Threat Model, Assumptions, and Boundaries

*VERA Protocol — Technical Whitepaper*
*Version 2.1 — May 2026*

---

## 4.1 Overview

This section formally specifies the security properties VERA provides, the operational assumptions under which those properties hold, and the attack classes that are explicitly outside the protocol's scope.

VERA is designed around a single governing principle:

> **VERA reduces systemic centralized risk, not absolute local risk.**

This distinction is not a limitation of design — it is a deliberate architectural choice. The threat landscape of modern privacy failures is dominated by centralized data accumulation, secondary reuse, industrial-scale behavioral profiling, and cross-service correlation. VERA's architecture directly targets this class of threat. It does not claim to address isolated local compromises, which represent a fundamentally different — and largely unsolved — problem even for hardware-backed trusted execution environments.

---

## 4.2 Threat Model

### 4.2.1 Attacker Classes

VERA considers four attacker classes with increasing privilege:

| Class | Description | VERA Posture |
|---|---|---|
| **A0 — Network Observer** | Passive interception of traffic between client and aggregation server | Defended: all transmitted data is differentially private noise |
| **A1 — Compromised Aggregation Server** | Full read access to server-side state and aggregate outputs | Defended: no raw data ever reaches the server; individual re-identification from aggregates is bounded by ε-differential privacy guarantees |
| **A2 — Malicious Platform Operator** | A licensed VERA operator deliberately attempting to bypass privacy guarantees | Partially defended: contractual and audit mechanisms; see §4.5 |
| **A3 — Compromised Client Binary** | An attacker with full control over the client device or application binary before noise injection | Out of scope: see §4.4 |

### 4.2.2 Primary Attack Surfaces

**Averaging attacks (TEST1A class).** TEST1A probes the confidentiality of the global aggregate mean under repeated LDP queries — a property that is mathematically unachievable for any Local Differential Privacy mechanism by the post-processing impossibility theorem: N independent noisy observations of the same true mean converge to that mean at rate O(1/√N), regardless of ε. This is not a VERA-specific limitation; it is a fundamental consequence of the LDP model. VERA therefore makes no claim of global-aggregate confidentiality. The guaranteed property — tested and confirmed in TEST1B — is individual-level protection: no single user's contribution is recoverable from any exported aggregate. The server-side invariants (K ≥ 100, TMoM, wK = 0.3, ε_total ≤ 1.5) enforce this separation. Selling the aggregate to AI operators is the intended use case; protecting who contributed what is the privacy guarantee.

**Coalition attacks.** A coalition of n ≥ K clients reporting correlated signals can, in principle, amplify the signal-to-noise ratio of the aggregate output. VERA's enforced invariants — specifically the kill-switch at ε_total > 1.5 and the coalition weight cap wK = 0.3 — are designed to bound this amplification. Heuristic coalition detection is implemented and flagged as a known limitation in §4.6.

**Epsilon jitter instability.** If the noise variance applied at the client layer is inconsistent across sessions, a timing-correlated observer may infer behavioral patterns from variance fluctuations rather than from signal values. VERA v4 enforces a fixed ε_client = 1.0 and ε_server = 0.5 across all pipeline executions. Jitter outside a defined tolerance triggers the kill-switch.

**Code tampering.** An attacker with write access to the VERA client binary can remove or disable noise injection before transmission. This does not produce detectable anomalies at the network or server layer if the tampered client otherwise conforms to the protocol envelope. The mitigating control is the Ed25519 audit chain: any aggregation produced without proper noise application will not carry a valid cryptographic signature matching the declared pipeline parameters. This does not prevent the attack; it makes the attack detectable post-hoc by auditors without requiring access to raw data.

---

## 4.3 Security Assumptions

VERA's guarantees are conditioned on the following assumptions. These are not aspirational — they are explicit preconditions. If any assumption is violated, the corresponding guarantee degrades as described.

**A1 — Honest noise injection.** The client-side VERA module applies Laplace noise with ε_client = 1.0 prior to any network transmission. *If violated:* individual-level privacy degrades to the privacy level of the raw signal. The audit chain will reflect the violation on review.

**A2 — Aggregation server does not retain pre-aggregation state.** The server processes incoming noisy signals into aggregate outputs and destroys intermediate data immediately. *If violated:* the server gains access to noisy (but not raw) individual signals, bounded by the LDP guarantee.

**A3 — K-anonymity threshold is enforced before export.** No aggregate is exported with a contributing population smaller than K = 100. *If violated:* small-group re-identification risk increases proportionally. The kill-switch is the primary enforcement mechanism.

**A4 — The epsilon budget is not exceeded.** The total privacy budget ε_total ≤ 1.5 is maintained across all queries and sessions for a given individual. *If violated:* the kill-switch halts processing. This is a hard system invariant, not a policy recommendation.

**A5 — The audit chain private key is not compromised.** Ed25519 signatures on aggregate outputs are valid only if the signing key remains under VERA's exclusive control. *If violated:* fraudulent audit proofs could be generated. Key rotation and RFC3161 timestamping provide detection capability.

---

## 4.4 Compromised Client: Scope Boundary

An attacker with full control of the client binary prior to noise injection — including root access, supply-chain compromise, hypervisor attacks, or physical access — can in principle extract raw data before VERA processes it. This is not a vulnerability in VERA's design; it is a property of all software-layer privacy systems.

For reference: Apple Secure Enclave Processor, Google Play Integrity, Microsoft Pluton, Intel SGX, and ARM TrustZone — the most advanced deployed hardware attestation systems — remain vulnerable to supply-chain attacks, side-channel extraction, kernel compromise, and physical fault injection. Any privacy protocol claiming to fully resolve the compromised-client problem would be making a false claim.

VERA's response to this boundary is architectural: rather than requiring trust in client hardware, VERA minimizes the quantity of trust required from the client to a single binary property:

> **VERA reduces client trust to a single verifiable binary condition: that Laplace noise with ε_client = 1.0 is applied to the raw signal before any network transmission occurs. All other system properties — server honesty, aggregator integrity, peer behavior — are verifiable by audit without access to raw data.**

This is a weaker property than hardware attestation. It is also deployable on any Android device without proprietary hardware dependencies, without vendor lock-in to Apple or Google attestation infrastructure, and without assumptions about enclave honesty.

---

## 4.5 Malicious Platform Operator

VERA is a B2B protocol. The entities that deploy and operate VERA — radio platforms, streaming services, AI operators — are the primary trust anchors in the system, not the end users. A platform operator that deliberately bypasses noise injection, retains raw data in violation of the SLA, or exports sub-K aggregates is the highest-privilege attacker class (A2).

VERA's technical controls against A2 are partial:

- The Ed25519 audit chain makes violations detectable by a third-party auditor without requiring access to raw data.
- RFC3161 timestamps anchor the audit chain to an external time reference, preventing retroactive falsification.
- The kill-switch invariants (ε_total kill at > 1.5, K kill at < 100) prevent accidental violation but do not prevent deliberate circumvention of the pipeline.

The primary defense against A2 is contractual and regulatory, not technical. The SLA defines binding thresholds (SPEARMAN_SLA ≥ 0.90, K ≥ 100, ε_total ≤ 1.5), and compliance is verifiable by independent audit of the signed aggregate chain. Deliberate, willful bypass by a platform operator is treated as a legal and regulatory matter — not a cryptographic one.

This is the correct scope boundary. Claiming cryptographic enforcement against a fully privileged operator who controls the deployment environment would be technically incoherent.

---

## 4.6 Rationale: VERA Does Not Require TEEs

A natural question for reviewers: why does VERA not mandate Trusted Execution Environments (SGX enclaves, TrustZone secure worlds, or equivalent) for client-side noise injection?

The answer is a deliberate architectural trade-off, not an oversight.

A TEE-mandatory design would provide stronger client-side attestation but would introduce the following costs:

- **Hardware dependency.** TEE availability varies significantly across Android devices, particularly in the fragmented sub-flagship market. A TEE requirement would exclude a substantial fraction of the target user base.
- **Vendor trust substitution.** TEE attestation delegates trust to hardware manufacturers (Intel, ARM, Qualcomm). This substitutes one trust assumption for another — one that is opaque, proprietary, and non-auditable by VERA or its clients.
- **Attack surface shift.** SGX has a documented history of side-channel vulnerabilities (Spectre variants, LVI, AEPIC Leak). Mandating SGX does not eliminate the compromised-client risk; it relocates it.
- **Deployment friction.** TEE integration requires platform-specific SDKs, manufacturer partnerships, and certification processes incompatible with VERA's open, auditable deployment model.

VERA's position is explicit:

> **VERA is designed to not depend on TEEs. This is a weaker cryptographic guarantee and a significantly more deployable system. The trade-off is intentional.**

The system remains coherent and its guarantees remain valid in an environment where client endpoints are imperfect — because the architecture does not assume endpoint perfection.

---

## 4.7 Deployment Trade-offs

| Property | TEE-Mandatory Design | VERA Design |
|---|---|---|
| Client attestation strength | Hardware-backed | Software audit chain |
| Android device compatibility | Partial (flagship-biased) | Universal |
| Vendor dependency | Intel / ARM / Qualcomm | None |
| Auditability | Opaque (proprietary enclave) | Open (Ed25519 + RFC3161) |
| Compromised-client resistance | Stronger (not absolute) | Weaker (bounded) |
| Deployment complexity | High | Low |
| Regulatory audit readiness | Indirect | Direct (open chain) |

VERA optimizes for universal deployability and open auditability over maximal client-side attestation strength. In the context of VERA's target deployment — licensed B2B integrations with radio platforms under SLA — the regulatory and contractual enforcement layer compensates for the weaker client trust model.

---

## 4.8 Non-Goals

The following are explicitly outside VERA's security scope:

1. **Confidentiality of the global aggregate mean.** VERA does not claim that aggregate outputs (trending tracks, listening distributions) are secret. They are designed to be shared with licensed B2B consumers. VERA guarantees only that individual contributions to those aggregates are not recoverable.

2. **Perfect forward secrecy for historical raw data.** VERA destroys raw data immediately after noise injection. There is no historical raw store to protect. However, VERA does not protect raw data that existed before VERA integration.

3. **Protection against a fully compromised client binary controlled by the attacker prior to noise injection.** This is a hardware-level trust problem outside the scope of any software privacy protocol.

4. **Verification that a platform operator has not deployed a modified VERA binary.** VERA provides audit evidence of what was computed; it does not provide remote attestation that the unmodified VERA binary was used.

5. **Anonymization of metadata external to the audio signal.** IP addresses, device fingerprints, and network metadata are outside VERA's processing pipeline and must be handled by the platform operator's own infrastructure.

---

## 4.9 Summary: Security Boundary

| Threat | VERA Coverage |
|---|---|
| Network interception of listening data | ✅ Fully defended |
| Server-side re-identification of individuals | ✅ Bounded by ε-DP + K-anonymity |
| Averaging attack on aggregate mean | ⚠️ Acknowledged — aggregate mean is not claimed confidential |
| Coalition signal amplification | ⚠️ Bounded by wK = 0.3 and kill-switch |
| Malicious platform operator (accidental) | ✅ Prevented by kill-switch invariants |
| Malicious platform operator (deliberate) | ⚠️ Detectable by audit; legal scope |
| Compromised client binary (pre-noise) | ❌ Out of scope — hardware trust problem |
| TEE-level attestation | ❌ Deliberately excluded — see §4.6 |

---

*End of Section 4.*

*Next section: Section 5 — Formal Privacy Guarantees and SLA Thresholds.*
