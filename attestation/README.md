# VERA — Hardware TEE Attestation Evidence

**Date:** 2026-05-23  
**Environment:** Google Cloud Confidential VM · AMD SEV-SNP  
**Kernel:** 6.17.0-1016-gcp  

## What this proves

A real SNP attestation report was obtained directly from `/dev/sev-guest`
via ioctl `0xC0205300` on a GCP N2D (AMD EPYC Milan) Confidential VM.

Evidence collected:
- `/dev/sev-guest` device present and responding
- ioctl SNP_GET_REPORT returned 1184 bytes (AMD spec-compliant size)
- Challenge nonce `VERA-1779518819` embedded by the CPU in the report
- Hardware measurement field non-zero (SHA-384 of enclave contents)
- Kernel flags: SEV + SEV-ES + SEV-SNP active

## Files

| File | Description |
|------|-------------|
| `vera_attestation.json` | Parsed attestation metadata |
| `report.bin` | Raw 1184-byte hardware report |
| `sha256.txt` | SHA-256 of report.bin |

## SHA-256 of raw report
git add attestation/
git commit -m "feat: add hardware TEE attestation evidence (AMD SEV-SNP, nonce-verified)"
git push

cat attestation/README.md | head -5

git add attestation/ && git commit -m "feat: add hardware TEE attestation evidence (AMD SEV-SNP, nonce-verified)" && git push

eof
