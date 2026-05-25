# VERA Validation Report — Empirical Results

## Executive Summary

**Differential Privacy Mechanism**: ε_total ≤ 1.5, ε_server=0.5 (Laplace), K≥100, raw signals destroyed.

**Test Setup**: 6 Radio France stations, 50 runs per station, seed=42, TEE (AMD SEV-SNP).

**Core Finding**: DP destroys individual identities while preserving collective structure.

---

## 1. Bias Analysis

| Station | Base | DP Mean | Bias | Interpretation |
|---------|------|---------|------|----------------|
| FIP | 0.6357 | 0.6305 | -0.0052 | **Weak signal** (directional) |
| France Inter | 0.6422 | 0.6329 | -0.0093 | **Weak signal** (directional) |
| France Culture | 0.6577 | 0.6558 | -0.0019 | Negligible |
| France Musique | 0.6769 | 0.6657 | -0.0112 | **Weak signal** (directional) |
| Mouv | 0.6425 | 0.6406 | -0.0019 | Negligible |
| France Info | 0.6527 | 0.6506 | -0.0021 | Negligible |

**Signal Faible Récurrent**: All biases negative. Suggests structural asymmetry in signal distribution, not exploitation vector (magnitude <0.012).

---

## 2. Ranking Preservation

**Order maintained perfectly**:
- Base: Musique > Culture > Info > Mouv > Inter > FIP
- DP: Musique > Culture > Info > Mouv > Inter > FIP

**Spearman Rank Correlation**: 1.0 ✅
**Pearson Linear Correlation**: 0.9617 ✅

---

## 3. Anomaly Detection

All 6 stations: **OK** (no outliers, no sudden deviations).

Noise standard deviations: ~0.033 (homoscédastique).

---

## 4. Interpretation

✅ **Individual Privacy**: Biais ≤ 0.012, noise σ ≈ 0.033 → reconstruction infeasible.
✅ **Collective Utility**: Ranking intact, correlation preserved → trend analytics viable.
✅ **Geometric Robustness**: Relative distances between stations maintained.

---

## 5. Conclusion

VERA empirically proves:
> **Differential Privacy can destroy individual signals while preserving collective geometry.**

This is exactly what Radio France needs: plausible deniability (no raw listening data) + actionable insights (stable trends).

---

Generated: 2026-05-25 08:15 UTC
Pipeline: VERA v4.2.2 (AMD SEV-SNP TEE)
