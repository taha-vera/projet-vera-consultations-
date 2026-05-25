# VERA v2 — Security Considerations for CCS/PETS

## Cryptographic Assumptions

HPKE (RFC 9180): IND-CCA secure
Ed25519: Existential unforgeability
SHA256: Collision resistant

## Threat Model Coverage

In Scope:
- A_external: HPKE encryption defends
- A_operator: Ciphertext blindness defends
- A_replay: Monotonic counter defends
- A_downgrade: Version binding defends

Out of Scope:
- A_tee_sideChannel: Spectre, LVI (CPU updates)
- A_clientCompromised: Malware (out of protocol)
- A_supplyChain: Hardware backdoor

## Implementation Security

Private keys: Ephemeral, sealed
Plaintext destruction: Triple-pass zeroize
Timing attacks: Constant-time crypto libs

## Testing Requirements

Mandatory CCS/PETS tests:
- test_reboot_replay
- test_attestation_binding
- test_downgrade_prevention
- test_signature_verification

All implemented and passing.
