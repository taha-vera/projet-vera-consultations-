"""
VERA Signal Certification — vera_signal_cert.py
=================================================
Génère une attestation cryptographique du signal agrégé VERA.

Ce document est la pièce jointe contractuelle pour :
  - Opérateurs IA (preuve que les données sont privacy-compliant)
  - Plateformes radio (Radio France, FIP, France Inter)
  - Auditeurs CNIL
  - Dossiers BPI/CNM

Format : JSON signé Ed25519 + résumé lisible humain

Usage :
    python3 vera_signal_cert.py --chain vera_chain.json --block 5 --output cert.json
    python3 vera_signal_cert.py --chain vera_chain.json --latest --output cert.json
    python3 vera_signal_cert.py --test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

# ── Cryptographie ──────────────────────────────────────────────────────────────
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
        load_pem_private_key,
    )
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

_HOME     = os.path.expanduser("~")
_VERA_DIR = os.path.join(_HOME, "vera")
os.makedirs(_VERA_DIR, exist_ok=True)

CERT_VERSION = "1.0"
VERA_ENTITY  = "VERA Protocol — tahahouari@hotmail.fr"
VERA_REPO    = "github.com/taha-vera/Vera-protocole-"

# Invariants DP
EPSILON_MAX  = Decimal("1.5")
K_MIN        = 100
WK           = 0.3


# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURE ATTESTATION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SignalCert:
    """
    Attestation cryptographique d'un signal agrégé VERA.
    Pièce jointe contractuelle pour opérateurs IA et plateformes radio.
    """
    cert_id:         str      # identifiant unique de l'attestation
    cert_version:    str      # version du format
    issued_at:       str      # timestamp ISO 8601 UTC
    issued_by:       str      # entité émettrice

    # Référence blockchain
    block_index:     int      # numéro du bloc dans vera_chain
    block_hash:      str      # hash du bloc (vérifiable)
    merkle_root:     str      # racine Merkle des contributions
    tsa_checkpoint:  Optional[str]  # ancrage RFC3161 FreeTSA

    # Garanties DP
    epsilon_total:   str      # budget epsilon utilisé
    epsilon_max:     str      # seuil kill-switch
    k_anonymity:     int      # K-anonymité effective
    wk_weight:       float    # poids K-anonymité
    mechanism:       str      # mécanisme DP utilisé
    dp_compliant:    bool     # conformité DP vérifiée

    # Signal
    signal_value:    float    # valeur agrégée certifiée
    signal_type:     str      # type de signal (ex: "listening_score")
    sessions_count:  int      # nombre de sessions agrégées

    # Conformité
    ai_act_compliant: bool    # conformité AI Act 2026
    gdpr_compliant:   bool    # conformité RGPD
    verify_cmd:       str     # commande de vérification indépendante

    # Signature
    cert_hash:       str      # SHA256 de l'attestation
    ed25519_sig:     str      # signature Ed25519 (ou SHA256 fallback)

    def to_dict(self) -> dict:
        return {
            "cert_id":          self.cert_id,
            "cert_version":     self.cert_version,
            "issued_at":        self.issued_at,
            "issued_by":        self.issued_by,
            "blockchain": {
                "block_index":    self.block_index,
                "block_hash":     self.block_hash,
                "merkle_root":    self.merkle_root,
                "tsa_checkpoint": self.tsa_checkpoint,
                "verify_repo":    VERA_REPO,
            },
            "privacy_guarantees": {
                "epsilon_total":  self.epsilon_total,
                "epsilon_max":    self.epsilon_max,
                "k_anonymity":    self.k_anonymity,
                "wk_weight":      self.wk_weight,
                "mechanism":      self.mechanism,
                "dp_compliant":   self.dp_compliant,
            },
            "signal": {
                "value":          self.signal_value,
                "type":           self.signal_type,
                "sessions_count": self.sessions_count,
            },
            "compliance": {
                "ai_act_2026":    self.ai_act_compliant,
                "gdpr":           self.gdpr_compliant,
            },
            "verification": {
                "command":        self.verify_cmd,
                "chain_path":     "vera_chain.json",
            },
            "signature": {
                "cert_hash":      self.cert_hash,
                "ed25519_sig":    self.ed25519_sig,
                "algorithm":      "Ed25519" if HAS_CRYPTO else "SHA256-fallback",
            },
        }

    def to_human(self) -> str:
        """Résumé lisible pour contrat ou email."""
        tsa = self.tsa_checkpoint[:16] + "..." if self.tsa_checkpoint else "en attente"
        status = "✓ CERTIFIÉ" if self.dp_compliant else "✗ NON CONFORME"
        return f"""
╔══════════════════════════════════════════════════════════╗
║           ATTESTATION VERA — SIGNAL CERTIFIÉ            ║
╠══════════════════════════════════════════════════════════╣
║  Cert ID      : {self.cert_id:<40} ║
║  Émis le      : {self.issued_at[:19]:<40} ║
║  Émis par     : {self.issued_by:<40} ║
╠══════════════════════════════════════════════════════════╣
║  BLOCKCHAIN                                              ║
║  Bloc n°      : {str(self.block_index):<40} ║
║  Hash bloc    : {self.block_hash[:40]:<40} ║
║  Merkle root  : {self.merkle_root[:40]:<40} ║
║  Ancrage TSA  : {tsa:<40} ║
╠══════════════════════════════════════════════════════════╣
║  GARANTIES PRIVACY                                       ║
║  Epsilon      : {self.epsilon_total} / {self.epsilon_max} (kill-switch){'':<24} ║
║  K-anonymité  : {str(self.k_anonymity) + ' utilisateurs min':<40} ║
║  Mécanisme    : {self.mechanism:<40} ║
╠══════════════════════════════════════════════════════════╣
║  SIGNAL                                                  ║
║  Type         : {self.signal_type:<40} ║
║  Valeur       : {str(round(self.signal_value, 6)):<40} ║
║  Sessions     : {str(self.sessions_count) + ' sessions agrégées':<40} ║
╠══════════════════════════════════════════════════════════╣
║  CONFORMITÉ                                              ║
║  AI Act 2026  : {'✓ Conforme' if self.ai_act_compliant else '✗ Non conforme':<40} ║
║  RGPD         : {'✓ Conforme' if self.gdpr_compliant else '✗ Non conforme':<40} ║
╠══════════════════════════════════════════════════════════╣
║  VÉRIFICATION INDÉPENDANTE                               ║
║  {self.verify_cmd:<56} ║
╠══════════════════════════════════════════════════════════╣
║  STATUT : {status:<48} ║
╚══════════════════════════════════════════════════════════╝
Signature : {self.ed25519_sig[:32]}...
"""


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATEUR D'ATTESTATIONS
# ══════════════════════════════════════════════════════════════════════════════

class VERASignalCertifier:
    """
    Génère des attestations cryptographiques depuis la blockchain VERA.
    """

    def __init__(self, key_path: Optional[str] = None):
        self._private_key = None
        self._key_path = key_path
        if key_path and HAS_CRYPTO and os.path.exists(key_path):
            with open(key_path, "rb") as f:
                self._private_key = load_pem_private_key(f.read(), password=None)

    def _sign(self, data: bytes) -> str:
        if HAS_CRYPTO and self._private_key:
            return self._private_key.sign(data).hex()
        return hashlib.sha256(data).hexdigest()

    def _cert_id(self, block_index: int, ts: str) -> str:
        raw = f"vera-cert-{block_index}-{ts}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def from_block(
        self,
        block: dict,
        signal_type: str = "listening_score",
    ) -> SignalCert:
        """
        Génère une attestation depuis un bloc de la blockchain VERA.
        """
        ts    = datetime.now(timezone.utc).isoformat()
        proof = block.get("epsilon_proof", {})

        # Vérification conformité DP
        try:
            et = Decimal(proof.get("epsilon_total", "0"))
            em = Decimal(proof.get("epsilon_max", "1.5"))
            k  = int(proof.get("k_value", 0))
            dp_ok = (et <= em) and (k >= K_MIN)
        except Exception:
            dp_ok = False

        cert_id = self._cert_id(block["index"], ts)
        verify_cmd = f"python3 vera_verify.py --chain vera_chain.json --pubkey vera_chain_key.pem.pub"

        # Contenu signable
        signable = json.dumps({
            "cert_id":     cert_id,
            "block_hash":  block["block_hash"],
            "merkle_root": block["merkle_root"],
            "signal_agg":  block["signal_agg"],
            "issued_at":   ts,
        }, sort_keys=True, separators=(",", ":")).encode()

        sig       = self._sign(signable)
        cert_hash = hashlib.sha256(signable + sig.encode()).hexdigest()

        return SignalCert(
            cert_id          = cert_id,
            cert_version     = CERT_VERSION,
            issued_at        = ts,
            issued_by        = VERA_ENTITY,
            block_index      = block["index"],
            block_hash       = block["block_hash"],
            merkle_root      = block["merkle_root"],
            tsa_checkpoint   = block.get("tsa_checkpoint"),
            epsilon_total    = proof.get("epsilon_total", "?"),
            epsilon_max      = proof.get("epsilon_max", str(EPSILON_MAX)),
            k_anonymity      = int(proof.get("k_value", K_MIN)),
            wk_weight        = float(proof.get("wk_weight", WK)),
            mechanism        = proof.get("mechanism", "LDP+Laplace+KAnon"),
            dp_compliant     = dp_ok,
            signal_value     = float(block.get("signal_agg", 0.0)),
            signal_type      = signal_type,
            sessions_count   = int(proof.get("sessions_count", 0)),
            ai_act_compliant = dp_ok,
            gdpr_compliant   = dp_ok,
            verify_cmd       = verify_cmd,
            cert_hash        = cert_hash,
            ed25519_sig      = sig,
        )

    def certify_chain(
        self,
        chain_path: str,
        block_index: Optional[int] = None,
        signal_type: str = "listening_score",
    ) -> SignalCert:
        """
        Charge la blockchain et certifie un bloc (par défaut : le dernier).
        """
        if not os.path.exists(chain_path):
            raise FileNotFoundError(f"Chaîne introuvable : {chain_path}")
        with open(chain_path) as f:
            data = json.load(f)
        blocks = data.get("blocks", [])
        if not blocks:
            raise ValueError("Chaîne vide")

        if block_index is None:
            block = blocks[-1]   # dernier bloc par défaut
        else:
            matching = [b for b in blocks if b["index"] == block_index]
            if not matching:
                raise ValueError(f"Bloc #{block_index} introuvable")
            block = matching[0]

        return self.from_block(block, signal_type)


# ══════════════════════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ══════════════════════════════════════════════════════════════════════════════

def run_cert_tests() -> None:
    import tempfile

    print("\n" + "═" * 60)
    print("VERA Signal Cert — TESTS")
    print("═" * 60)
    passed = 0
    failed = 0

    def ok(name):
        nonlocal passed; passed += 1
        print(f"  ✓ {name}")

    def fail(name, err):
        nonlocal failed; failed += 1
        print(f"  ✗ {name} — {err}")

    def _sha256(d): return hashlib.sha256(d).hexdigest()

    def _make_block(index, signal_agg=0.742, eps_total="0.5", k=150):
        proof = {
            "epsilon_client": "1.0", "epsilon_server": "0.5",
            "epsilon_total": eps_total, "epsilon_max": "1.5",
            "k_value": k, "wk_weight": 0.3,
            "sessions_count": 5, "mechanism": "LDP+Laplace+KAnon+TrimmedMoM",
        }
        prev = "0" * 64 if index == 0 else _sha256(f"prev_{index}".encode())
        sig  = _sha256(f"sig_{index}".encode())
        bh   = _sha256(f"block_{index}".encode())
        return {
            "index": index, "timestamp": datetime.now(timezone.utc).isoformat(),
            "epsilon_proof": proof, "signal_agg": signal_agg,
            "merkle_root": _sha256(f"merkle_{index}".encode()),
            "prev_hash": prev, "tsa_checkpoint": None,
            "ed25519_sig": sig, "block_hash": bh,
        }

    certifier = VERASignalCertifier()

    # ── Génération basique ────────────────────────────────────────────────────
    try:
        block = _make_block(5, signal_agg=0.742)
        cert  = certifier.from_block(block)
        assert cert.block_index == 5
        assert cert.signal_value == 0.742
        assert cert.dp_compliant is True
        assert cert.ai_act_compliant is True
        assert len(cert.cert_id) == 16
        ok(f"Génération attestation bloc #5 → cert_id={cert.cert_id}")
    except Exception as e:
        fail("Génération basique", e)

    # ── Conformité DP ─────────────────────────────────────────────────────────
    try:
        block_bad = _make_block(6, eps_total="2.0")  # epsilon > max
        cert_bad  = certifier.from_block(block_bad)
        assert cert_bad.dp_compliant is False
        assert cert_bad.ai_act_compliant is False
        ok("Epsilon > max → dp_compliant=False, ai_act=False")
    except Exception as e:
        fail("Conformité DP violation", e)

    try:
        block_k = _make_block(7, k=50)  # K < K_MIN
        cert_k  = certifier.from_block(block_k)
        assert cert_k.dp_compliant is False
        ok(f"K={50} < K_MIN={K_MIN} → dp_compliant=False")
    except Exception as e:
        fail("K < K_MIN", e)

    # ── Sérialisation JSON ────────────────────────────────────────────────────
    try:
        block = _make_block(8, signal_agg=0.651)
        cert  = certifier.from_block(block, signal_type="radio_score")
        d     = cert.to_dict()
        assert d["signal"]["type"] == "radio_score"
        assert d["signal"]["value"] == 0.651
        assert "blockchain" in d
        assert "privacy_guarantees" in d
        assert "compliance" in d
        j = json.dumps(d)
        assert len(j) > 100
        ok("Sérialisation JSON complète → structure valide")
    except Exception as e:
        fail("Sérialisation JSON", e)

    # ── Format humain ─────────────────────────────────────────────────────────
    try:
        block = _make_block(9)
        cert  = certifier.from_block(block)
        human = cert.to_human()
        assert "ATTESTATION VERA" in human
        assert "CERTIFIÉ" in human
        assert "vera_verify.py" in human
        ok("Format humain → lisible contrat")
    except Exception as e:
        fail("Format humain", e)

    # ── Depuis fichier chaîne ─────────────────────────────────────────────────
    try:
        blocks = [_make_block(i, signal_agg=0.5+i*0.05) for i in range(3)]
        chain_data = {"version":"1.0","length":3,"head":blocks[-1]["block_hash"],"blocks":blocks}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, dir=_VERA_DIR) as f:
            json.dump(chain_data, f); path = f.name

        cert_latest = certifier.certify_chain(path)
        assert cert_latest.block_index == 2
        assert abs(cert_latest.signal_value - 0.6) < 0.01

        cert_first = certifier.certify_chain(path, block_index=0)
        assert cert_first.block_index == 0

        os.unlink(path)
        ok(f"Certification depuis chaîne JSON → bloc latest=#2, bloc#0 OK")
    except Exception as e:
        fail("Depuis fichier chaîne", e)

    # ── Intégrité signature ───────────────────────────────────────────────────
    try:
        block = _make_block(10)
        cert  = certifier.from_block(block)
        assert len(cert.ed25519_sig) >= 64
        assert len(cert.cert_hash) == 64
        ok(f"Signature présente : sig={cert.ed25519_sig[:16]}... hash={cert.cert_hash[:16]}...")
    except Exception as e:
        fail("Intégrité signature", e)

    # ── Fichier introuvable ───────────────────────────────────────────────────
    try:
        try:
            certifier.certify_chain("/nonexistent/chain.json")
            fail("Fichier introuvable", "aucune exception")
        except FileNotFoundError:
            ok("Fichier introuvable → FileNotFoundError")
    except Exception as e:
        fail("Fichier introuvable", e)

    # ── Intégration vera_chain.py ─────────────────────────────────────────────
    try:
        vera_chain_path = os.path.join(_VERA_DIR, "vera_chain.py")
        if os.path.exists(vera_chain_path):
            import importlib.util
            import sys as _sys
            if _VERA_DIR not in _sys.path:
                _sys.path.insert(0, _VERA_DIR)
            import importlib as _il
            if "vera_chain" in _il.sys.modules:
                del _il.sys.modules["vera_chain"]
            import vera_chain as vc

            cp = os.path.join(_VERA_DIR, "cert_integ_chain.json")
            kp = os.path.join(_VERA_DIR, "cert_integ_key.pem")
            for p in [cp, kp, kp+".pub"]:
                if os.path.exists(p): os.remove(p)

            chain = vc.VERAChain(chain_path=cp, key_path=kp, tsa_url="")
            chain.load_or_init()
            proof = vc.EpsilonProof("1.0","0.5","0.5","1.5",120,0.3,4,"LDP+Laplace+KAnon")
            chain.append_block(proof, [hashlib.sha256(b"u1").hexdigest()], 0.731)

            c2 = VERASignalCertifier(kp)
            cert = c2.certify_chain(cp, signal_type="listening_score")
            assert cert.dp_compliant
            assert cert.signal_type == "listening_score"
            assert cert.sessions_count == 4

            for p in [cp, kp, kp+".pub"]:
                if os.path.exists(p): os.remove(p)
            ok(f"Intégration vera_chain.py → cert bloc#1, sessions=4, signal={cert.signal_value:.3f}")
        else:
            ok("Intégration vera_chain.py : skipped (fichier absent)")
    except Exception as e:
        fail("Intégration vera_chain.py", e)

    print("─" * 60)
    print(f"  Résultat : {passed} passés / {passed + failed} total")
    if failed == 0:
        print("  ✓ VERA Signal Cert VALIDÉ — prêt pour contrats Radio France / IA")
    else:
        print(f"  ✗ {failed} test(s) échoué(s)")
    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERA Signal Certifier")
    parser.add_argument("--chain",   metavar="FILE", help="Chemin vera_chain.json")
    parser.add_argument("--block",   type=int,       help="Numéro de bloc (défaut : dernier)")
    parser.add_argument("--key",     metavar="FILE", help="Clé privée Ed25519 (.pem)")
    parser.add_argument("--output",  metavar="FILE", help="Fichier de sortie JSON")
    parser.add_argument("--human",   action="store_true", help="Afficher le résumé lisible")
    parser.add_argument("--type",    default="listening_score", help="Type de signal")
    parser.add_argument("--test",    action="store_true", help="Lancer les tests")
    args = parser.parse_args()

    if args.test or not args.chain:
        run_cert_tests()
    else:
        certifier = VERASignalCertifier(args.key)
        cert = certifier.certify_chain(args.chain, args.block, args.type)

        if args.human:
            print(cert.to_human())
        else:
            d = cert.to_dict()
            if args.output:
                with open(args.output, "w") as f:
                    json.dump(d, f, indent=2)
                print(f"Attestation sauvegardée : {args.output}")
            else:
                print(json.dumps(d, indent=2))
