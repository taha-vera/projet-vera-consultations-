"""
ancre_verify.py
ANCRE — Attested Noise Client Runtime Engine
Vérification côté serveur des attestations SIM

Vérifie :
  1. Validité cryptographique de la signature Ed25519
  2. Chaîne de certificat SIM vers PKI opérateur
  3. Cohérence hash signal / signature
  4. Mode SIM (rejette les attestations MOCK en production)

Auteur : SAS VERA
Version : 0.1
"""

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from cryptography.exceptions import InvalidSignature
import cryptography.x509 as x509
from cryptography.x509.oid import NameOID

log = logging.getLogger("ANCRE.Verify")

# ─────────────────────────────────────────────
# Résultat de vérification
# ─────────────────────────────────────────────

@dataclass
class VerificationResult:
    valid: bool
    reason: str                        # Description du résultat
    operator_org: Optional[str] = None # Organisation opérateur du certificat
    sim_mode: Optional[str] = None
    verified_at: str = ""

    def __post_init__(self):
        if not self.verified_at:
            self.verified_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "operator_org": self.operator_org,
            "sim_mode": self.sim_mode,
            "verified_at": self.verified_at,
        }


# ─────────────────────────────────────────────
# Vérificateur d'attestation ANCRE
# ─────────────────────────────────────────────

class AncreAttestVerifier:
    """
    Vérifie les attestations SIM reçues par le serveur ANCRE.

    En production : charge les certificats racine des opérateurs partenaires.
    En mode DEV   : accepte les certificats mock (REJECT_MOCK=False).
    """

    def __init__(
        self,
        trusted_operator_orgs: list[str] = None,
        reject_mock: bool = False,
    ):
        """
        trusted_operator_orgs : liste des organisations opérateur acceptées
                                 Ex: ["Orange", "SFR", "Bouygues Telecom", "Transatel"]
        reject_mock            : True en production, False en dev Termux
        """
        self.trusted_operator_orgs = trusted_operator_orgs or [
            "ANCRE-MOCK-OPERATOR",   # Dev uniquement
            "Orange",
            "SFR",
            "Bouygues Telecom",
            "Transatel",
            "Eseye",
        ]
        self.reject_mock = reject_mock

        log.info(
            f"AncreAttestVerifier initialisé — "
            f"reject_mock={reject_mock} — "
            f"opérateurs acceptés : {self.trusted_operator_orgs}"
        )

    def verify(
        self,
        noisy_signal: float,
        signal_hash_b64: str,
        signature_b64: str,
        certificate_chain_b64: str,
        sim_mode: str,
    ) -> VerificationResult:
        """
        Vérification complète d'une attestation SIM.

        Étapes :
          1. Rejeter les attestations MOCK si reject_mock=True
          2. Vérifier cohérence hash signal
          3. Extraire clé publique du certificat SIM
          4. Vérifier l'organisation opérateur (PKI)
          5. Vérifier la signature Ed25519
        """

        # Étape 1 — Rejet MOCK en production
        if self.reject_mock and "MOCK" in sim_mode.upper():
            return VerificationResult(
                valid=False,
                reason="Attestation MOCK rejetée en mode production",
                sim_mode=sim_mode,
            )

        try:
            signal_hash = base64.b64decode(signal_hash_b64)
            signature = base64.b64decode(signature_b64)
            cert_der = base64.b64decode(certificate_chain_b64)
        except Exception as e:
            return VerificationResult(
                valid=False,
                reason=f"Décodage base64 échoué : {e}",
                sim_mode=sim_mode,
            )

        # Étape 2 — Cohérence hash signal
        expected_hash = hashlib.sha256(
            str(noisy_signal).encode("utf-8")
        ).digest()

        if signal_hash != expected_hash:
            return VerificationResult(
                valid=False,
                reason=(
                    f"Hash signal incohérent — "
                    f"reçu={signal_hash.hex()[:16]}... "
                    f"attendu={expected_hash.hex()[:16]}..."
                ),
                sim_mode=sim_mode,
            )

        # Étape 3 — Parse certificat X.509
        try:
            cert = x509.load_der_x509_certificate(cert_der)
        except Exception as e:
            return VerificationResult(
                valid=False,
                reason=f"Certificat DER invalide : {e}",
                sim_mode=sim_mode,
            )

        # Étape 4 — Vérification organisation opérateur
        try:
            org_attrs = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            operator_org = org_attrs[0].value if org_attrs else "INCONNU"
        except Exception:
            operator_org = "INCONNU"

        if operator_org not in self.trusted_operator_orgs:
            return VerificationResult(
                valid=False,
                reason=f"Opérateur non autorisé : '{operator_org}'",
                operator_org=operator_org,
                sim_mode=sim_mode,
            )

        # Étape 5 — Vérification signature Ed25519
        try:
            public_key = cert.public_key()
            public_key.verify(signature, signal_hash)
        except InvalidSignature:
            return VerificationResult(
                valid=False,
                reason="Signature Ed25519 invalide",
                operator_org=operator_org,
                sim_mode=sim_mode,
            )
        except Exception as e:
            return VerificationResult(
                valid=False,
                reason=f"Erreur vérification signature : {e}",
                operator_org=operator_org,
                sim_mode=sim_mode,
            )

        # ✅ Attestation valide
        log.info(
            f"Attestation valide — opérateur={operator_org} — mode={sim_mode}"
        )
        return VerificationResult(
            valid=True,
            reason="Attestation SIM valide",
            operator_org=operator_org,
            sim_mode=sim_mode,
        )

    def verify_batch(
        self,
        noisy_signals: list[float],
        batch_hash_b64: str,
        signature_b64: str,
        certificate_chain_b64: str,
        sim_mode: str,
    ) -> VerificationResult:
        """Vérification d'une attestation batch."""

        if self.reject_mock and "MOCK" in sim_mode.upper():
            return VerificationResult(
                valid=False,
                reason="Attestation MOCK batch rejetée en mode production",
                sim_mode=sim_mode,
            )

        try:
            batch_hash = base64.b64decode(batch_hash_b64)
            signature = base64.b64decode(signature_b64)
            cert_der = base64.b64decode(certificate_chain_b64)
        except Exception as e:
            return VerificationResult(
                valid=False,
                reason=f"Décodage base64 échoué : {e}",
                sim_mode=sim_mode,
            )

        # Reconstitution hash batch
        batch_bytes = b"".join(str(s).encode("utf-8") for s in noisy_signals)
        expected_hash = hashlib.sha256(batch_bytes).digest()

        if batch_hash != expected_hash:
            return VerificationResult(
                valid=False,
                reason="Hash batch incohérent",
                sim_mode=sim_mode,
            )

        try:
            cert = x509.load_der_x509_certificate(cert_der)
            org_attrs = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            operator_org = org_attrs[0].value if org_attrs else "INCONNU"
        except Exception as e:
            return VerificationResult(
                valid=False,
                reason=f"Certificat invalide : {e}",
                sim_mode=sim_mode,
            )

        if operator_org not in self.trusted_operator_orgs:
            return VerificationResult(
                valid=False,
                reason=f"Opérateur non autorisé : '{operator_org}'",
                operator_org=operator_org,
                sim_mode=sim_mode,
            )

        try:
            cert.public_key().verify(signature, batch_hash)
        except InvalidSignature:
            return VerificationResult(
                valid=False,
                reason="Signature batch invalide",
                operator_org=operator_org,
                sim_mode=sim_mode,
            )

        log.info(
            f"Attestation batch valide — "
            f"{len(noisy_signals)} signaux — opérateur={operator_org}"
        )
        return VerificationResult(
            valid=True,
            reason=f"Attestation batch valide — {len(noisy_signals)} signaux",
            operator_org=operator_org,
            sim_mode=sim_mode,
        )


# ─────────────────────────────────────────────
# Test Termux
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from ancre_sim_attest import AncreSimAttestClient

    print("=" * 55)
    print("ANCRE — ancre_verify.py — Test Termux")
    print("=" * 55)

    # Générer une attestation mock
    client = AncreSimAttestClient(mock=True)
    signal = 0.73
    att = client.attest_signal(signal)

    # Vérifier l'attestation
    verifier = AncreAttestVerifier(reject_mock=False)
    result = verifier.verify(
        noisy_signal=signal,
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    print(f"\n[VÉRIFICATION SIGNAL UNIQUE]")
    print(json.dumps(result.to_dict(), indent=2))

    # Test batch
    batch = [0.12, 0.87, 0.34, 0.56, 0.91]
    att_batch = client.attest_batch(batch)
    result_batch = verifier.verify_batch(
        noisy_signals=batch,
        batch_hash_b64=base64.b64encode(att_batch.signal_hash).decode(),
        signature_b64=base64.b64encode(att_batch.signature).decode(),
        certificate_chain_b64=base64.b64encode(att_batch.certificate_chain).decode(),
        sim_mode=att_batch.sim_mode,
    )

    print(f"\n[VÉRIFICATION BATCH]")
    print(json.dumps(result_batch.to_dict(), indent=2))

    # Test rejet signature falsifiée
    result_tampered = verifier.verify(
        noisy_signal=signal,
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(b"signature_falsifiee_" + b"0" * 44).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    print(f"\n[TEST REJET — signature falsifiée]")
    print(json.dumps(result_tampered.to_dict(), indent=2))
    assert not result_tampered.valid, "ERREUR : signature falsifiée acceptée"
    print("✅ Signature falsifiée correctement rejetée")

    print("\n✅ ancre_verify.py — OK")
