# VERA: A Differential Privacy Protocol for Aggregate Signal Preservation

**Authors**: Taha Houari  
**Version**: 2.1 (Post-DeepSeek Red-Team)  
**Date**: May 2026  
**Status**: VERA_CORE_v1_FREEZE

## 1. Problem Statement
[...]

## 5. Observed Limitations

### 5.1 Directional Bias: Data Asymmetry + Clipping
Raw data is long-tail. Symmetric clamp on asymmetric distribution 
creates negative bias. Detectable but not reconstructible.

### 5.2 Ranking Leakage: Spearman=1.0 is Measurement Artifact
Perfect ranking is not guaranteed. Empirically observed on 6 stations,
but likely due to large inter-artist gaps. We claim Spearman > 0.95 in general,
not 1.0.

### 5.3 K≥100: Empirical Engineering, Not DP Fundamental
Laplace works at any K. K=100 is operational threshold
(error acceptable for Radio France editorial decisions).

### 5.4 TEE: Attestation is the Core Defense
Without attestation = illusory. With attestation (VERA model) = robust.
Remaining threat = supply chain / microcode (infrastructure scope).

## References
[...]

---
**Red-Team**: DeepSeek (2026-05-25)
**Result**: 4 challenges, 3 passed, 1 clarified
