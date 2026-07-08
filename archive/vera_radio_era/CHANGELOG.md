# VERA Protocol — Changelog

## v0.3.0 — 2026-06-04 (current)

### Security
- feat(dp): getrandom OS entropy — cryptographic RNG replaces LCG+timestamp
- feat(dp): Discrete Laplace — resistant to Mironov 2012 float attack
- fix(spine): zeroize — raw values erased from RAM after aggregation

### Tests
- test(spine): 4 adversarial tests — biased injection, temporal drift, reidentification, gaming
- test(spine): end-to-end pipeline — ingestion to redistribution
- chore: clippy fixes — 0 warnings across workspace

### Total: 37 tests, 0 failed, 0 warnings

---

## v0.2.0 — SDK + Economic Model

### Features
- feat(sdk): vera-radio-sdk v0.1 — 3-line integration, k-fallback
- feat(sdk): vera-client-sdk v0.1 — purchase, redistribution 70/30
- fix(sdk): redistribution model 70/30 — VERA neutral, SACEM decides internal split
- feat(dp): BudgetTracker — formal DP composition

### Benchmark
- Spearman rho=1.0000 on Last.fm real data
- K effective=119, latency=0.134ms/artist

---

## v0.1.0 — Core Protocol

### Features
- feat(cli): vera CLI v0.1.0 — setup/test/deploy/audit/import
- feat(radio): vera-radio v0.1.0 — FFT capture + DP export
- lock: VERA SPINE v3.1.1 LOCKED — 5 formal invariants

### Documentation
- docs: VERA whitepaper v1.0
- docs: README — 6 modules, results, invariants

---

*VERA Protocol — github.com/taha-vera/Protocole-Vera*
