## Empirical Validation — Formal Compatibility Tests

### Data
6 Radio France stations, 50 runs each, AMD SEV-SNP TEE execution.

### Results

| Test | Result | Value |
|---|---|---|
| t-test (bias) | p<0.01 | t=-3.27, mean_e=-0.005 |
| IC 95% | 0 excluded | [-0.0080, -0.0020] |
| Bland-Altman LoA | stable bias | [-0.0123, +0.0023] |
| VERA Score | COMPATIBLE | 0.325 < 1.0 |
| Pearson | PASS | 0.961 > 0.95 |
| Spearman | PASS | 1.000 |

### Interpretation

The DP mechanism introduces a systematic offset of -0.005 (t=-3.27, p<0.01),
consistent with expected clamp and trimming effects at epsilon=0.5. This bias
is operationally negligible (VERA score=0.325) and confirms the mechanism is
well-calibrated — not a structural anomaly. Pearson (0.961) and Spearman (1.0)
confirm full preservation of collective signal structure.

Note: Base and DP mean originate from the same pipeline. The only difference
is DP noise injection. This is a standard DP fidelity test, not a two-method
comparison.
