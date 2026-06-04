# VERA Protocol

**Verifiable Extraction and Redistribution Architecture**

Open-source privacy-preserving infrastructure for ethical AI training data.
VERA aggregates weak recurring signals from cultural sources (radio, music)
and makes them available to AI operators as legally compliant training data.

> "VERA fills a gap nobody wants to solve because it is currently
> in their interest to ignore it."

---

## Why VERA

| Problem | VERA Solution |
|---------|--------------|
| AI scrapes data illegally | Privacy-preserving aggregation by design |
| Artists receive nothing | Mandatory redistribution (Invariant IV) |
| No auditability | 31 validated tests + formal proofs |
| High energy cost | Non-persistence + zeroize = minimal footprint |

**Energy advantage:** VERA stores nothing. Raw signals are erased after
aggregation. No petabyte storage. No deduplication pipelines.
A lighter protocol means lower carbon footprint for every AI operator.

---

## Three-Actor Ecosystem

VERA connects three actors as a neutral trusted infrastructure:

- Radio / Media — provide cultural signals, receive revenue share
- SACEM / Rights holders — represent artists, receive new AI-era compensation
- AI Operators — purchase legal auditable training data

VERA does not replace collective management organizations.
It provides the measurement, audit, and redistribution layer.

---

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| vera-sib/spine | Core protocol — 5 invariants + DP | v3.1.1 |
| vera-radio | FFT audio capture + privacy export | v0.2 |
| vera-sib | Empirical validation RSR/CSC/SUR/PHL | 9/9 |
| vera-cli | Automation — setup/test/deploy/audit/import | v0.1 |
| vera-benchmark | Economic proof — Last.fm real data | rho=1.0 |
| vera-pulse | Opt-in contributors + redistribution | Planned |

---

## Results

| Metric | Value | Meaning |
|--------|-------|---------|
| Spearman rho | 1.0000 | Signal utility perfectly preserved |
| K effective | 119 users | K-anonymity respected |
| Latency | 0.134ms/artist | Production ready |
| RSR | 0.53 | Reconstruction impossible |
| CSC | 1e-6 | No cross-session correlation |
| SUR | 0.97 | 97% signal utility retained |
| PHL | 1h | Temporal decay validated |
| Tests | 31 passed | 0 failed |

---

## Five Formal Invariants

VERA SPINE v3.1.1 enforces five invariants by code, not policy:

1. Non-persistence — raw signals erased after aggregation (zeroize)
2. Irreversible aggregation — k-anonymity >= 100, no reconstruction possible
3. Temporal decay — data loses weight over time, half-life 24h
4. Mandatory redistribution — revenue automatically distributed to contributors
5. Separation of powers — layers cannot access each other

---

## Quick Start

    git clone https://github.com/taha-vera/Protocole-Vera
    cd Protocole-Vera
    cargo build --workspace
    cargo test --workspace --lib
    ./target/debug/vera test

---

## Security

- Discrete Laplace — resistant to Mironov 2012 float attack
- Formal DP BudgetTracker — composition enforced
- Zeroize — raw values erased from RAM after aggregation
- See VERA_THREAT_MODEL_COMPLETE.md

---

## License

Open-source — see LICENSE

## Contact

Repository: github.com/taha-vera/Protocole-Vera
Email: tahahouari@hotmail.fr

VERA Protocol — privacy-preserving, model-agnostic, open-source.

## Test Coverage

| Category | Tests |
|----------|-------|
| Security | reject_nan_in_ingest, reject_nan_in_revenue, reject_inf_in_ingest, reject_mixed_nan_values |
| Differential Privacy | test_budget_exhausted, test_budget_remaining, test_budget_consume_ok, test_dlap_output_bounded, test_dlap_no_float_holes |
| VERA Invariants | prop_decay_monotone, prop_decay_in_unit_interval, prop_redistribution_sum_exact |
| Stress | stress_1k_cohorts_100k_graphlets, stress_redistribution_500_cohorts, stress_purge_1000_graphlets, stress_float_accumulation |
| Serialization | serial_golden_snapshot, serial_graphlet_no_raw_value, serial_graphlet_mean_preserved |
| SDK Radio | test_three_lines_integration, test_no_export_below_k100, test_budget_decreases |
| SDK Client | test_purchase_ok, test_budget_exceeded, test_redistribution_model |

Total: 34 tests, 0 failed.
