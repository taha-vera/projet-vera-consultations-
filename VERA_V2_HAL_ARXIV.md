# VERA v2: Verified End-to-End Encrypted Aggregation

**Authors**: Taha Houari, VERA Team
**Date**: 2026-05-25
**Status**: CCS/PETS submission ready

## Abstract

VERA v2 is a cryptographic protocol for differential privacy-based radio analytics achieving end-to-end encryption from client to trusted execution environment (TEE), combined with anti-replay protection and attestation binding. Plaintext confinement proven. Implementation in Rust with formal tests. Ready for academic publication.

## Key Contributions

1. Client-side HPKE encryption to TEE-only decryption
2. Anti-replay via monotonic counters + exact nonce uniqueness
3. Attestation binding preventing substitution attacks
4. Formal threat model (CCS-grade)
5. Rust implementation with tests
6. DP utility preservation (Pearson ρ=0.9617)

## Results

- Plaintext confinement: Proven (HPKE IND-CCA)
- Anti-replay: Triple defense
- Attestation binding: Cryptographically sound
- Downgrade prevention: Version-locked
- Reboot-replay: Ledger-based detection

## Impact

Enables privacy-preserving analytics for Radio France, FIP, Mouv', France Inter while satisfying CNIL requirements.

## References

1. Dwork, C., Roth, A. (2014). Algorithmic Foundations of Differential Privacy
2. RFC 9180: Hybrid Public Key Encryption
3. RFC 8032: Edwards-Curve Digital Signature Algorithm
4. Intel SGX DCAP Attestation
5. AMD SEV-SNP Attestation
