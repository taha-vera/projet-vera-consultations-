# VERA Protocol — Whitepaper v2.0

**Version:** 2.0
**Date:** 2026-06-05
**Repository:** github.com/taha-vera/Protocole-Vera
**Status:** Living document — aligned with proof protocol vision

---

## Abstract

VERA (Verifiable Extraction and Redistribution Architecture) is an
open-source proof protocol for cultural data processing.

VERA is not a company. Not a financial intermediary. Not a platform.

VERA enforces a set of immutable technical invariants and produces
verifiable cryptographic evidence about the processing of cultural signals.

When data transits through VERA, raw signals are destroyed.
What remains are orphaned statistics — aggregated, irreversible,
untraceable to any individual source or work.

This certified destruction is the core value of VERA.

For AI operators, it provides technical documentation for regulatory compliance.

For collective management organizations such as SACEM, it provides
verifiable proof that cultural signals were processed — enabling
them to exercise redistribution rights according to their own rules.

VERA does not collect money.
VERA does not redistribute revenue.
VERA certifies.

---

## Section 1 — The Problem

### 1.1 AI Training Data is Legally Contested

AI models require vast amounts of cultural data for training.
Current data acquisition practices face three critical challenges:

- Legal risk: scraping cultural content without consent violates copyright and GDPR
- No proof: AI operators cannot demonstrate that training data was processed lawfully
- No traceability: artists and rights holders have no evidence that their works contributed to AI training

### 1.2 Nobody Wants to Solve This

The problem persists because it is currently in the interest
of major AI actors to ignore it.

Scraping is cheap. Legal risk is deferred.
Artists are not organized enough to enforce their rights at scale.
Regulators are catching up slowly.

VERA is built for the moment this changes — which is now,
with the AI Act entering into force in 2026.

---

## Section 2 — What VERA Is

### 2.1 A Proof Protocol

VERA is a proof protocol.

Its purpose is to process cultural signals through a set of
immutable technical invariants and produce verifiable evidence
that the processing occurred correctly.

The output of VERA is not data. It is proof.

Proof that raw signals were destroyed.
Proof that aggregation was irreversible.
Proof that privacy constraints were enforced.
Proof that the signal transited through a compliant implementation.

### 2.2 What VERA Is Not

VERA is not a platform.
VERA is not a marketplace.
VERA is not a financial intermediary.
VERA is not a collective management organization.
VERA does not collect money.
VERA does not redistribute revenue.
VERA does not manage copyrights or neighboring rights.

These functions belong to the organizations that choose
to deploy or use VERA.

### 2.3 The Analogy

VERA is to cultural data what a notary is to a contract.

The notary does not own the contract.
The notary does not enforce the contract.
The notary certifies that the contract was signed correctly.

VERA certifies that cultural data was processed correctly.
What happens next is not VERA's concern.

---

## Section 3 — The Five Invariants

VERA enforces five invariants by code, not policy.
These invariants are immutable.
An implementation that violates them is not VERA.

### Invariant I — Non-Persistence

Raw signals are never stored.
They are destroyed immediately after aggregation.
No raw audio, no raw cultural data, no individual signal
ever leaves the collection layer.

### Invariant II — Irreversible Aggregation

Only statistical aggregates are produced.
k-anonymity threshold >= 100 is enforced.
No individual contribution can be reconstructed
from the aggregate output.

### Invariant III — Temporal Decay

Aggregated data loses weight over time.
Half-life: 24 hours. Maximum validity: 30 days.
This ensures that the protocol does not accumulate
long-term profiles of any kind.

### Invariant IV — Certified Destruction

VERA produces cryptographic evidence that raw data was destroyed.
This certification is the technical proof that collective
management organizations need to exercise their rights.

VERA does not redistribute. VERA certifies.
The redistribution — if any — is decided and executed
by the organizations that use VERA's certification.

### Invariant V — Separation of Powers

Collection, aggregation, and export layers are strictly separated.
No layer can access the data of another.
This architectural separation is enforced by code.

---

## Section 4 — The Three Actors

VERA operates at the intersection of three actors.
VERA serves all three. VERA is controlled by none.

### 4.1 Radio Stations and Media

Radio stations and media organizations provide cultural signals.
What they gain: verifiable proof that their content was processed
lawfully, enabling them to claim compensation through collective
management organizations.

### 4.2 Collective Management Organizations

Organizations such as SACEM, SCPP, ADAMI represent artists
and rights holders.

What they gain: VERA's certification provides the technical
evidence they need to prove that cultural works contributed
to AI training — without identifying which specific work,
without storing any raw signal.

VERA does not replace these organizations.
VERA provides the proof they need to do their job.

### 4.3 AI Operators

AI operators need high-quality cultural training data that is
legally defensible under the AI Act and GDPR.

What they gain: VERA provides the technical documentation
required by AI Act Article 53 — automatically, auditably,
at zero cost.

VERA does not sell data to AI operators.
VERA certifies that data was processed correctly.
AI operators use this certification as legal documentation.

---

## Section 5 — Technical Validation

### 5.1 Implementation

VERA SPINE v3.1.1 is implemented in Rust.
The five invariants are enforced by 39 automated tests
across four platforms.

### 5.2 Differential Privacy

VERA implements Discrete Laplace mechanism —
resistant to the Mironov 2012 floating-point attack.
A formal BudgetTracker enforces DP composition.
Cryptographic entropy via getrandom (OS-level).

### 5.3 Empirical Validation — Radio France

Six Radio France stations were captured and processed
through the VERA analysis pipeline for 3 hours.

Results:
- Six stations produced statistically distinct signatures
- Signatures remain stable over time
- Raw audio was destroyed — only orphaned statistics remain
- Separability score at epsilon=1.0: 0.20
  (decreasing monotonically with epsilon, as expected)

Note: this analysis used a Python reference implementation.
Full Rust pipeline integration via vera-radio is in progress.

### 5.4 Test Coverage

| Category | Tests | Status |
|----------|-------|--------|
| Security | 4 | PASS |
| Differential Privacy | 5 | PASS |
| VERA Invariants | 3 | PASS |
| Stress | 4 | PASS |
| Serialization | 3 | PASS |
| Adversarial | 4 | PASS |
| Integration | 1 | PASS |
| SDK | 6 | PASS |
| SIB empirical | 9 | PASS |

Total: 39 tests, 0 failed.

---

## Section 6 — Legal Value

### 6.1 The Regulatory Context

The AI Act enters into force in 2026.
Article 53 requires AI operators to document their
training data sources and processing methods.

GDPR Article 17 requires that personal data be erasable.
VERA is designed to minimize the need for erasure by avoiding
persistence of raw data by design.

### 6.2 What VERA's Proof Means Legally

VERA's cryptographic certification that raw data was destroyed
constitutes technical documentation that:

- No personal data was retained
- Processing occurred according to documented invariants
- The resulting statistics are mathematically orphaned

This documentation can contribute to an AI operator's
compliance posture under the AI Act and GDPR.

Note: VERA's legal value should be confirmed by formal
legal analysis in each jurisdiction. VERA provides the
technical foundation — legal interpretation requires
qualified legal counsel.

### 6.3 For Artists

VERA certifies that cultural signals transited through the protocol.
This certification enables collective management organizations to:

- Prove that cultural works contributed to AI training
- Exercise their redistribution rights under existing law
- Negotiate compensation with AI operators

VERA does not determine compensation.
VERA does not enforce payment.
VERA certifies the fact of processing.
What follows is decided by humans and institutions.

---

## Section 7 — Roadmap

| Phase | Milestone | Status |
|-------|-----------|--------|
| 1 | VERA SPINE v3.1.1 — 5 invariants | DONE |
| 1 | Differential Privacy — Discrete Laplace | DONE |
| 1 | vera-radio — FFT capture | DONE |
| 1 | vera-sib — empirical validation | DONE |
| 1 | vera-cli — automation | DONE |
| 1 | Radio France — real data validation | DONE |
| 2 | vera-radio Rust pipeline — real stream | IN PROGRESS |
| 2 | Zenodo DOI — citable reference | PLANNED |
| 3 | SACEM partnership outreach | PLANNED |
| 3 | CNIL filing | PLANNED |
| 4 | PETS 2027 academic submission | PLANNED |

---

## Conclusion

VERA fills a gap that nobody wants to fill because it is
currently in the interest of major AI actors to ignore it.

The gap is this: there is no open, neutral, auditable way
to process cultural data for AI training while certifying
that the raw material was destroyed.

VERA is that protocol.

Not a platform. Not a business. Not a financial actor.

A protocol. With invariants. Open-source. For everyone.

The code runs. The tests pass. The invariants hold.
The proof is generated automatically.

What the actors do with that proof is their responsibility.

---

*VERA Protocol v2.0*
*github.com/taha-vera/Protocole-Vera*
*taha-vera.github.io/Protocole-Vera*
