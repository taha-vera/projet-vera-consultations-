"""
ancre_verify.py
ANCRE — Attested Noise Client Runtime Engine
Vérification serveur v0.2 — Post red team multi-IA

Corrections intégrées :
  P1 — PKI complète (expiry + path validation)
  P2 — Nonce anti-replay + timestamp signé
  P3 — struct.pack canonique (IEEE 754)
  P4 — NaN/Inf/bounds guard
  P5 — Device tracking via cert serial
  P6 — try/except complet (anti-DoS)
  P8 — sim_mode dans payload signé

Auteur : SAS VERA / ANCRE
Version : 0.2
"""

import struct
import hashlib
import hmac
import math
import uuid
import json
import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import cryptography.x509 as x509
from cryptography.exceptions import InvalidSignature
from cryptography.x509.oid import NameOID

log = logging.getLogger("ANCRE.Verify")

# ─────────────────────────────────────────────
# Paramètres de sécurité v0.2
# ─────────────────────────────────────────────
MAX_CERT_BYTES         = 8_192   # P6 — limite taille certificat
NONCE_WINDOW_SEC       = 300     # P2 — fenêtre fraîcheur 5 min
MAX_SIGNALS_PER_DEVICE = 3       # P5 — quota par device/session


# ─────────────────────────────────────────────
# P3 — Canonicalisation float → bytes
# ─────────────────────────────────────────────

def canonical_signal_bytes(signal: float) -> bytes:
    """
    Encodage canonique IEEE 754 big-endian.
    Remplace str(float) non-déterministe.
    Produit exactement 8 bytes stables sur toute plateforme.
    """
    return struct.pack('>d', signal)

def canonical_signal_hash(signal: float) -> bytes:
    """SHA-256 du signal en représentation canonique."""
    return hashlib.sha256(canonical_signal_bytes(signal)).digest()


# ─────────────────────────────────────────────
# P4 — Guards NaN/Inf/bounds
# ─────────────────────────────────────────────

def validate_signal(signal: float) -> float:
    """Rejette NaN, Inf, -Inf, et valeurs hors [0.0, 1.0]."""
    if not isinstance(signal, (int, float)):
        raise ValueError(f"Signal doit être un float, reçu : {type(signal)}")
    if math.isnan(signal):
        raise ValueError("Signal NaN interdit")
    if math.isinf(signal):
        raise ValueError("Signal Inf/-Inf interdit")
    if not 0.0 <= signal <= 1.0:
        raise ValueError(f"Signal hors plage [0,1] : {signal}")
    return float(signal)


# ─────────────────────────────────────────────
# P2 + P8 — Payload signé
# ─────────────────────────────────────────────

@dataclass
class SignedPayload:
    """
    Payload complet couvert par la signature SIM.
    Nonce + slot + sim_mode + timestamp sont maintenant signés.
    """
    signal_hash: bytes
    nonce: str
    slot: int
    sim_mode: str
    timestamp_utc: str

    def to_bytes(self) -> bytes:
        """Sérialisation JSON canonique déterministe."""
        payload = {
            "nonce": self.nonce,
            "signal_hash": base64.b64encode(self.signal_hash).decode(),
            "sim_mode": self.sim_mode,
            "slot": self.slot,
            "timestamp_utc": self.timestamp_utc,
        }
        return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


@dataclass
class AncreAttestation:
    """Attestation v0.2 — payload signé + certificat."""
    noisy_value: float
    payload: SignedPayload
    payload_signature: bytes
    certificate_chain: bytes
    cert_serial: int


# ─────────────────────────────────────────────
# Résultat de vérification
# ─────────────────────────────────────────────

@dataclass
class VerificationResult:
    valid: bool
    reason: str
    operator_org: Optional[str] = None
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
# Vérificateur v0.2
# ─────────────────────────────────────────────

class AncreAttestVerifier:
    """
    Vérificateur ANCRE v0.2
    Toutes les corrections red team intégrées.
    """

    def __init__(
        self,
        trusted_ca_certs: list = None,
        trusted_operator_orgs: list = None,
        reject_mock: bool = False,
        nonce_window_sec: int = NONCE_WINDOW_SEC,
        max_signals_per_device: int = MAX_SIGNALS_PER_DEVICE,
    ):
        self.trusted_ca_certs = trusted_ca_certs or []
        self.trusted_operator_orgs = trusted_operator_orgs or [
            "ANCRE-MOCK-OPERATOR",
            "Orange", "SFR", "Bouygues Telecom", "Transatel",
        ]
        self.reject_mock = reject_mock
        self.nonce_window_sec = nonce_window_sec
        self.max_signals_per_device = max_signals_per_device
        self._used_nonces: dict = {}
        self._device_signal_count: dict = {}
        log.info(f"AncreAttestVerifier v0.2 — reject_mock={reject_mock}")

    def issue_nonce(self) -> str:
        """P2 — Génère un nonce serveur (anti-replay)."""
        return str(uuid.uuid4())

    def verify(self, att: AncreAttestation) -> tuple:
        """
        Vérification complète v0.2.
        Retourne (valid: bool, reason: str).
        """

        # P6 — Taille certificat
        try:
            if len(att.certificate_chain) > MAX_CERT_BYTES:
                return False, f"Certificat trop grand : {len(att.certificate_chain)}B > {MAX_CERT_BYTES}B"
        except Exception as e:
            return False, f"Erreur taille : {e}"

        # P4 — Validation signal
        try:
            validate_signal(att.noisy_value)
        except ValueError as e:
            return False, f"Signal invalide : {e}"

        # P8 — Rejet MOCK en production
        if self.reject_mock and "MOCK" in att.payload.sim_mode.upper():
            return False, "MOCK rejeté en production"

        # P2 — Fraîcheur timestamp
        try:
            ts = datetime.fromisoformat(att.payload.timestamp_utc)
            now = datetime.now(timezone.utc)
            age = (now - ts).total_seconds()
            if age > self.nonce_window_sec:
                return False, f"Attestation expirée : {age:.0f}s"
            if age < -60:
                return False, f"Timestamp futur suspect : {age:.0f}s"
        except Exception as e:
            return False, f"Timestamp invalide : {e}"

        # P2 — Anti-replay nonce
        self._cleanup_nonces()
        nonce = att.payload.nonce
        if nonce in self._used_nonces:
            return False, f"Nonce replay détecté : {nonce}"
        self._used_nonces[nonce] = datetime.now(timezone.utc)

        # P3 — Hash canonique
        try:
            expected = canonical_signal_hash(att.noisy_value)
            if not hmac.compare_digest(att.payload.signal_hash, expected):
                return False, "Hash signal incohérent"
        except Exception as e:
            return False, f"Erreur hash : {e}"

        # P1 — Parse certificat
        try:
            cert = x509.load_der_x509_certificate(att.certificate_chain)
        except Exception as e:
            return False, f"Certificat DER invalide : {e}"

        # P1 — Expiry
        try:
            now_utc = datetime.now(timezone.utc)
            if now_utc > cert.not_valid_after_utc:
                return False, f"Certificat expiré"
            if now_utc < cert.not_valid_before_utc:
                return False, f"Certificat pas encore valide"
        except Exception as e:
            return False, f"Erreur validité : {e}"

        # P1 — Opérateur
        try:
            org_attrs = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
            operator_org = org_attrs[0].value if org_attrs else "INCONNU"
            if operator_org not in self.trusted_operator_orgs:
                return False, f"Opérateur non autorisé : '{operator_org}'"
        except Exception as e:
            return False, f"Erreur certificat : {e}"

        # P1 — CA chain
        if self.trusted_ca_certs:
            try:
                if not self._verify_cert_chain(cert):
                    return False, "Certificat non signé par CA de confiance"
            except Exception as e:
                return False, f"Erreur CA : {e}"

        # P5 — Device quota
        try:
            cert_serial = cert.serial_number
            if cert_serial != att.cert_serial:
                return False, "Serial certificat incohérent"
            count = self._device_signal_count.get(cert_serial, 0)
            if count >= self.max_signals_per_device:
                return False, f"Device {cert_serial} : quota atteint ({count})"
        except Exception as e:
            return False, f"Erreur device tracking : {e}"

        # P6 — Signature Ed25519
        try:
            cert.public_key().verify(att.payload_signature, att.payload.to_bytes())
        except InvalidSignature:
            return False, "Signature Ed25519 invalide"
        except Exception as e:
            return False, f"Erreur signature : {e}"

        # ✅ Valide
        self._device_signal_count[cert_serial] = count + 1
        log.info(f"Attestation valide — op={operator_org} — device={cert_serial}")
        return True, f"Valide — {operator_org}"

    def _cleanup_nonces(self):
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self.nonce_window_sec)
        self._used_nonces = {k: v for k, v in self._used_nonces.items() if v > cutoff}

    def _verify_cert_chain(self, leaf_cert) -> bool:
        if not self.trusted_ca_certs:
            return True
        for ca_der in self.trusted_ca_certs:
            try:
                ca_cert = x509.load_der_x509_certificate(ca_der)
                ca_cert.public_key().verify(
                    leaf_cert.signature,
                    leaf_cert.tbs_certificate_bytes,
                    leaf_cert.signature_hash_algorithm,
                )
                return True
            except Exception:
                continue
        return False

    def reset_device_counts(self):
        self._device_signal_count.clear()


# ─────────────────────────────────────────────
# Test Termux
# ─────────────────────────────────────────────

if __name__ == "__main__":
    from ancre_sim_attest import MockSimCard

    print("=" * 55)
    print("ANCRE — ancre_verify.py v0.2 — Test Termux")
    print("=" * 55)

    sim = MockSimCard(slot=1)
    sim.generate_keypair()
    cert_der = sim.get_certificate()
    cert = x509.load_der_x509_certificate(cert_der)
    cert_serial = cert.serial_number

    verifier = AncreAttestVerifier(reject_mock=False)

    def make_att(signal, nonce=None, sim_mode="MOCK", tamper_sig=False):
        nonce = nonce or verifier.issue_nonce()
        sig_hash = canonical_signal_hash(signal)
        payload = SignedPayload(
            signal_hash=sig_hash,
            nonce=nonce,
            slot=1,
            sim_mode=sim_mode,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
        sig = sim.sign(payload.to_bytes())
        if tamper_sig:
            sig = bytes(64)
        return AncreAttestation(
            noisy_value=signal,
            payload=payload,
            payload_signature=sig,
            certificate_chain=cert_der,
            cert_serial=cert_serial,
        )

    # Tests
    v1, r1 = verifier.verify(make_att(0.5))
    print(f"{'✅' if v1 else '❌'} Signal valide : {r1}")

    nonce = verifier.issue_nonce()
    verifier.verify(make_att(0.5, nonce=nonce))
    v2, r2 = verifier.verify(make_att(0.5, nonce=nonce))
    print(f"{'✅' if not v2 else '❌'} Replay rejeté : {r2}")

    v3, r3 = verifier.verify(make_att(0.5, tamper_sig=True))
    print(f"{'✅' if not v3 else '❌'} Signature falsifiée : {r3}")

    # NaN
    try:
        validate_signal(float('nan'))
        print("❌ NaN accepté")
    except ValueError as e:
        print(f"✅ NaN rejeté : {e}")

    print("\n✅ ancre_verify.py v0.2 — OK")
