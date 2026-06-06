# VERA Protocol

VERA is a proof protocol.

VERA does not collect money. VERA does not redistribute. VERA certifies.

When data transits through VERA, raw signals are destroyed. What remains are orphaned statistics.

## Five Invariants

1. Non-persistence
2. Irreversible aggregation
3. Temporal decay
4. Certified Destruction
5. Separation of powers

## Three Actors

- Radio / Media
- SACEM / Rights holders
- AI Operators

VERA does not replace collective management organizations.
VERA provides the proof they need to do their job.

## Tests

39 tests, 0 failed, 4 platforms.

github.com/taha-vera/Protocole-Vera


## Architecture Note

The active pipeline is implemented in Rust (vera-sib, vera-radio, vera-sdk, vera-cli).
Python scripts in archive/ are analysis utilities used during development.
All protocol invariants are enforced by Rust code only.
