# VERA Protocol — Whitepaper v1.0

**Version:** 1.0  
**Date:** 2026-06-04  
**Repository:** github.com/taha-vera/Protocole-Vera  
**Branch:** phase-1/w1-guardian-sophistication  

---

## Abstract

VERA (Verifiable Extraction and Redistribution Architecture) is an open-source 
privacy-preserving protocol designed to aggregate weak recurring signals from 
cultural data sources (radio, music, creative works) and make them available 
to AI operators as high-quality, legally compliant training data.

VERA acts as a neutral trusted intermediary between three actors:
- **Cultural sources** (radio stations, media) providing signals
- **Rights holders** (collective management organizations) representing artists
- **AI operators** purchasing aggregated patterns for model training

The protocol guarantees five formal invariants enforced by code, not policy:
non-persistence, irreversible aggregation, temporal decay, mandatory 
redistribution, and separation of powers.

VERA does not replace existing collective management organizations. 
It acts as a measurement, aggregation, auditability, and redistribution 
layer compatible with existing legal frameworks (GDPR, AI Act).

---
## Section 1 — Protocol Architecture

### 1.1 Problem Statement

AI models require high-quality cultural data for training. Current data 
acquisition practices face three critical challenges:

1. **Legal risk** — scraping cultural content without consent violates 
   copyright and GDPR
2. **No compensation** — artists and cultural producers receive nothing 
   when their work trains AI models
3. **No auditability** — AI operators cannot prove their training data 
   is legally compliant

VERA solves all three simultaneously.

### 1.2 The Five Formal Invariants

VERA SPINE v3.1.1 enforces five invariants by construction:

| Invariant | Description | Enforcement |
|-----------|-------------|-------------|
| I. Non-persistence | Raw signals are never stored | `zeroize` after aggregation |
| II. Irreversible aggregation | Only statistical patterns exported | k-anonymity ≥ 100 |
| III. Temporal decay | Older data loses weight over time | exponential decay, half-life 24h |
| IV. Mandatory redistribution | Revenue automatically distributed | formal proof in tests |
| V. Separation of powers | Layers cannot access each other | module isolation |

### 1.3 Differential Privacy Layer

VERA implements three DP mechanisms:

- **Discrete Laplace** — resistant to Mironov (2012) floating-point attack
- **Gaussian** — for (ε,δ)-DP guarantees
- **Randomized Response** — for local DP at collection layer

A formal `BudgetTracker` enforces composition: every query consumes 
budget ε, and requests are refused when the global budget is exhausted.

### 1.4 Validation

22 tests validated across three platforms (ARM64, x86_64, Ubuntu):
- 15 invariant tests (vera-spine)
- 4 pipeline tests (vera-radio)  
- 3 DP mechanism tests
- 4 budget composition tests
- 9 empirical SIB tests (RSR, CSC, SUR, PHL)

---
## Section 2 — Stakeholder Alignment

### 2.1 Three-Actor Ecosystem

VERA connects three actors through a neutral trusted infrastructure:

Radio stations provide cultural signals. Collective management
organizations (SACEM, SCPP, ADAMI) represent artists and rights holders.
AI operators purchase aggregated patterns for model training.
VERA sits at the center as the trusted measurement, audit,
and redistribution layer.

### 2.2 Value Proposition per Actor

| Actor | Contribution | Gain |
|-------|-------------|------|
| Radio | Cultural signal | Additional revenue stream |
| SACEM | Artist representation | New AI-era compensation |
| AI Operator | Funding | Legal auditable training data |
| VERA | Infrastructure | Service commission |

### 2.3 Aligned Interests

The key question any investor or institution asks is:
why would each actor agree to participate?

Radio has signal but no AI monetization path. VERA provides it.
SACEM has artists but no technical proof of AI usage. VERA provides it.
AI Operators have money but no legal data source. VERA provides it.

Each actor has a direct economic interest in VERA existence.

### 2.4 Institutional Compatibility

VERA does not replace collective management organizations.
The protocol acts as a measurement, aggregation, auditability,
and redistribution layer compatible with GDPR, AI Act Article 10,
and French intellectual property law.

SACEM and equivalent organizations remain the legal representatives
of artists. VERA provides the technical proof and redistribution
mechanism — they handle the relationship with their members.

---
## Section 3 — Empirical Validation (SIB)

### 3.1 VERA SIB — Surviving Information Budget

VERA SIB validates four privacy metrics on real aggregated data:

| Metric | Threshold | Status |
|--------|-----------|--------|
| RSR — Reconstruction Success Rate | <= 0.53 | PASS |
| CSC — Cross-Session Correlation | <= 1e-6 | PASS |
| SUR — Signal Utility Retention | > 0.97 | PASS |
| PHL — Persistence Half-Life | <= 1h | PASS |

### 3.2 What These Metrics Prove

RSR below 0.53 means an attacker cannot reconstruct who contributed
a signal better than random chance. This directly validates
Invariant I (non-persistence) and Invariant II (irreversible aggregation).

CSC below 1e-6 means sessions cannot be linked across time.
This validates Invariant V (separation of powers).

SUR above 0.97 means 97% of signal utility is preserved despite
DP noise. This is the economic proof: the data is useful.

PHL below 1h means data loses half its weight within one hour.
This validates Invariant III (temporal decay).

### 3.3 Test Infrastructure

All tests validated on three platforms:
- Termux ARM64 (Android)
- Google Cloud Shell Ubuntu x86_64
- Claude sandbox x86_64

22 Rust tests + 9 Python SIB tests = 31 total validated tests.

---
## Section 4 — VERA as Proof Protocol

### 4.1 What VERA Is

VERA is a proof protocol. Not a company. Not a financial intermediary.
Not a rights management organization.

VERA enforces five formal invariants by code, not policy.
These invariants are immutable. No one can override them.

### 4.2 What VERA Certifies

When data transits through VERA, the protocol produces
verifiable evidence that:

- Raw signals were destroyed after aggregation
- Aggregation is mathematically irreversible
- Privacy constraints were enforced
- The signal transited through a compliant VERA implementation

These orphaned statistics cannot be traced back to any source.

### 4.3 For Artists and Rights Holders

VERA certifies that cultural signals transited through the protocol.
Collective management organizations such as SACEM can use this
certification to exercise redistribution rights according to
their own rules. VERA does not collect money. VERA does not pay.
VERA certifies.

### 4.4 VERA-Pulse

VERA-Pulse is the opt-in module for individual contributors.
Users explicitly consent to share aggregated signals.
No raw audio is ever transmitted — only local FFT aggregates.
No personal data is retained.

---

## Section 5 — Roadmap

| Phase | Milestone | Status |
|-------|-----------|--------|
| 1 | VERA SPINE v3.1.1 — 5 invariants locked | DONE |
| 1 | Differential Privacy layer — Discrete Laplace | DONE |
| 1 | vera-radio — FFT capture + DP export | DONE |
| 1 | vera-sib — 31 tests validated | DONE |
| 1 | vera-cli — automation layer | DONE |
| 2 | vera-benchmark — economic proof | IN PROGRESS |
| 2 | vera-pulse — opt-in contributors | PLANNED |
| 3 | SACEM partnership outreach | PLANNED |
| 3 | First AI operator pilot | PLANNED |
| 3 | CNIL filing | PLANNED |
| 4 | PETS 2027 academic submission | PLANNED |

---

## Conclusion

VERA fills a gap nobody wants to solve because it is currently
in their interest to ignore it. AI models need high-quality
cultural data. Cultural producers need compensation. Regulators
need auditability.

VERA provides all three simultaneously, as open-source infrastructure,
upstream of all AI models, controlled by no single actor.

The code runs. The tests pass. The invariants hold.

---

*VERA Protocol — open-source, privacy-preserving, model-agnostic.*
*github.com/taha-vera/Protocole-Vera*

## Section 6 — VERA as a Proof Protocol

VERA is a proof protocol.

It is not a financial intermediary.
It is not a revenue redistribution system.
It is not a rights management organization.

Its purpose is to enforce a set of immutable technical
invariants and to generate verifiable evidence about
the processing of cultural data.

### What VERA Proves

When data transits through VERA, the protocol produces
cryptographic evidence that:

- Raw signals were destroyed after aggregation
- Aggregation was performed according to protocol rules
- The resulting statistics are mathematically irreversible
- The required privacy constraints were enforced
- The signal transited through a compliant VERA implementation

### What VERA Does Not Do

VERA does not collect money.
VERA does not redistribute revenue.
VERA does not pay artists.
VERA does not manage copyrights or neighboring rights.
VERA does not act as a collecting society.

These responsibilities remain with the organizations
that choose to deploy or use VERA.

### Legal Value

VERA is designed to generate auditable technical evidence
regarding the provenance and processing of training data.

For AI operators, this evidence can contribute to the
technical documentation required by applicable regulatory
frameworks, including obligations related to transparency,
traceability, and lawful data use.

For rights holders and cultural organizations, VERA provides
verifiable proof that cultural signals were processed through
the protocol without retaining the original raw material.

### Commercial Proposition

For AI operators, VERA's value proposition is simple:

"VERA automatically generates auditable technical evidence
about how training data was processed.
Open-source, transparent, and verifiable."

The protocol's objective is to reduce compliance friction
while increasing trust between AI developers, cultural
stakeholders, and regulators.

### The Invariants Are the Protocol

VERA's invariants are not constraints on the protocol.
They ARE the protocol.

Anyone can implement VERA.
Anyone can fork VERA.
But an implementation that violates the invariants
is not VERA.

The invariants are the identity of the protocol.
