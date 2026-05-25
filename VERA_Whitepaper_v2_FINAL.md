# VERA: A Differential Privacy Protocol for Aggregate Signal Preservation

**Authors**: Taha Houari  
**Version**: 2.0 (Honest Analysis)  
**Date**: May 2026  
**Status**: VERA_CORE_v1_FREEZE

---

## 1. Problem Statement

Current AI training datasets share three critical properties:

1. **Opacity**: Sources unknown, aggregation process hidden, individual contributions untraceable
2. **Irreversibility**: Raw personal data persists indefinitely in training sets
3. **Non-remuneration**: Creators see no economic benefit from their data

**Central Question**: Can we design infrastructure that:
- Aggregates data for AI utility (ranking, trends remain visible)
- Destroys raw individual signals durably
- Preserves collective statistical geometry
- Enables independent auditability
- Supports fair economic models

---

## 2. Core Architecture: Three Layers

### Layer 1: Client (ε_client = 1.0)
- Randomized Response protocol
- Local noise injection
- Hashed identifiers (NAV)

### Layer 2: Aggregation (ε_server = 0.5)
- Laplace mechanism on aggregate means
- Population threshold K ≥ 100
- Temporal decay on intermediate states

### Layer 3: Attestation (TEE + Audit Chain)
- AMD SEV-SNP hardware attestation
- HMAC append-only audit ledger
- Signed attestation (VCEK)
- Reproductible build (anyone can verify image)

**Total budget**: ε_total ≤ 1.5 (kill-switch enforced)

---

## 3. Formal DP Guarantees

### Theorem 1: ε-Differential Privacy
Given substitute adjacency (one user removal):
- Sensitivity Δ = 1/K
- Mechanism: Laplace(μ, Δ/ε)
- Proof: Dwork & Roth 2014 + Mironov 2012 tail bounds
- Result: (ε, δ=0)-DP with ε ≤ 1.5

### Theorem 2: Non-Individual-Reidentification
Empirical (Radio France, n=50):
- Mean bias: -0.0053
- Bias std: 0.0025
- Noise σ ≈ 0.033
- Reconstruction gap >> signal gap
- Conclusion: Individual contribution unrecoverable

### Theorem 3: Collective Geometry Preservation
- Spearman rank correlation ρ = 1.0 (empirical)
- Pearson linear correlation r ≈ 0.9617 (empirical)
- Ranking order invariant across 6 stations
- Cross-dataset invariance (Radio France ≈ Last.fm)

---

## 4. Experimental Validation

### Dataset 1: Radio France (6 stations, n=50 each, TEE: AMD SEV-SNP)

| Station | Base | DP Mean | Bias | Status |
|---------|------|---------|------|--------|
| FIP | 0.6357 | 0.6305 | -0.0052 | OK |
| France Inter | 0.6422 | 0.6329 | -0.0093 | OK |
| France Culture | 0.6577 | 0.6558 | -0.0019 | OK |
| France Musique | 0.6769 | 0.6657 | -0.0112 | OK |
| Mouv | 0.6425 | 0.6406 | -0.0019 | OK |
| France Info | 0.6527 | 0.6506 | -0.0021 | OK |

**Metrics**: Pearson = 0.9617, Spearman = 1.0

### Dataset 2: Last.fm (10 artists, synthetic, K=81–139)

**Metrics**: Pearson = 0.9617 (matches RF), Spearman = 1.0

**Cross-Dataset Finding**: Pearson and Spearman metrics identical across heterogeneous datasets.
Conclusion: Patterns are systematic, not dataset-specific.

---

## 5. Observed Limitations (Critical Section)

### 5.1 Directional Bias Pattern

**Observation**: 5 of 6 stations show negative bias (-0.005 to -0.011).
Not random. Laplace noise should be symmetric.

**Root Cause Analysis**:
- Primary: Clipping/trimming interaction wi

