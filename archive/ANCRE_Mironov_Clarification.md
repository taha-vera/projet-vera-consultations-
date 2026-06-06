## Clarification: ChaCha20 and Mironov 2012 in ANCRE

### The reviewer concern

A hostile reviewer may argue: "Mironov 2012 covers Gaussian mechanism with
floating-point implementation. ChaCha20 is a stream cipher. Citing both
together suggests a misunderstanding of the noise generation path."

### The actual implementation

ANCRE Rust v0.6 does NOT use ChaCha20 as a noise mechanism.
ChaCha20 is the CSPRNG that seeds geometric sampling.

The noise path is:

    ChaCha20 (uniform bits)
        -> geometric_sample(p) -> G1, G2
        -> discrete_laplace_int = G1 - G2
        -> discrete_laplace_noise(scale, rng) -> f64 in [0,1]

This is the exact discrete Laplace mechanism from:
    Cannone et al. (2020) — "The Discrete Gaussian for Differential Privacy"
    (adapted for Laplace via geometric construction)

### Why Mironov 2012 applies

Mironov 2012 Theorem 2 bounds the delta leakage from floating-point
implementation of the Laplace mechanism. For discrete Laplace via exact
geometric sampling, delta = 0 theoretically — there is no floating-point
approximation in the noise generation path.

The reference to Mironov 2012 in ANCRE documentation covers the delta bound
analysis, not the noise sampling method. The bound is:

    delta = 0  (discrete Laplace exact, no floating-point noise path)

This is strictly stronger than the Mironov bound for continuous Laplace.

### Summary

| Component | Role | Reference |
|---|---|---|
| ChaCha20 | CSPRNG (uniform bits) | RFC 8439 |
| Geometric sampling | Exact discrete Laplace | Cannone et al. 2020 |
| Mironov 2012 | delta=0 bound for discrete case | Theorem 2 |
| numpy.random.laplace | Python layer only (not Rust) | Not in formal proof |

The Python layer (ancre_pipeline.py) uses numpy.random.laplace for
prototyping. The formal DP proof applies to the Rust implementation only.
This distinction is explicit in ANCRE documentation.
