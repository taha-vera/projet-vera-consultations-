"""
VERA Chain — vera_chain.py
===========================
Blockchain légère VERA (Mai 2026) — Bloc 2

Structure de bloc :
  index          : numéro séquentiel
  timestamp      : ISO 8601 UTC
  epsilon_proof  : {epsilon_client, epsilon_server, epsilon_total, K, wK}
  signal_agg     : agrégat trimmed median-of-means (JAMAIS les valeurs brutes)
  merkle_root    : racine de l'arbre de Merkle des contributions
  prev_hash      : SHA256 du bloc précédent (chaîne)
  ed25519_sig    : signature Ed25519 du bloc complet

Checkpoint RFC3161 automatique tous les CHECKPOINT_INTERVAL blocs.

Vérification indépendante : python3 vera_chain.py --verify vera_chain.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import threading
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

# ── Cryptographie ──────────────────────────────────────────────────────────────
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding, NoEncryption, PrivateFormat, PublicFormat,
    )
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] vera.chain — %(message)s",
)
logger = logging.getLogger("vera.chain")

# ── Constantes ────────────────────────────────────────────────────────────────
CHECKPOINT_INTERVAL = 1          # Ancrage RFC3161 tous les N blocs
FREЕТSA_URL         = "https://freetsa.org/tsr"
GENESIS_PREV_HASH   = "0" * 64    # Hash du bloc genesis
CHAIN_VERSION       = "1.0"

# Invariants DP (cohérents avec vera_hardened_v5)
EPSILON_CLIENT  = Decimal("1.0")
EPSILON_SERVER  = Decimal("0.5")
EPSILON_TOTAL   = Decimal("1.5")
K_MIN           = 100
WK              = 0.3

_HOME     = os.path.expanduser("~")
_VERA_DIR = os.path.join(_HOME, "vera")
os.makedirs(_VERA_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class ChainIntegrityError(Exception):
    """Violation de l'intégrité de la chaîne."""

class ChainSignatureError(Exception):
    """Signature Ed25519 invalide."""

class EpsilonProofError(Exception):
    """Preuve epsilon invalide ou hors contrat."""


# ══════════════════════════════════════════════════════════════════════════════
# MERKLE TREE
# ══════════════════════════════════════════════════════════════════════════════

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def merkle_root(leaves: List[str]) -> str:
    """
    Calcule la racine de l'arbre de Merkle depuis une liste de hash feuilles.
    Chaque feuille est le hash SHA256 d'une contribution anonymisée.
    """
    if not leaves:
        return _sha256(b"empty")
    nodes = [_sha256(leaf.encode()) for leaf in leaves]
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])   # duplication du dernier nœud si impair
        nodes = [
            _sha256((nodes[i] + nodes[i + 1]).encode())
            for i in range(0, len(nodes), 2)
        ]
    return nodes[0]


# ══════════════════════════════════════════════════════════════════════════════
# EPSILON PROOF
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class EpsilonProof:
    """
    Preuve formelle des paramètres DP utilisés pour ce bloc.
    Auto-explicatif pour un auditeur CNIL sans documentation externe.
    """
    epsilon_client:  str   # "1.0"
    epsilon_server:  str   # "0.5"
    epsilon_total:   str   # valeur cumulée au moment du bloc
    epsilon_max:     str   # "1.5" (seuil kill-switch)
    k_value:         int   # K-anonymité effective
    wk_weight:       float # poids K-anonymité (0.3)
    sessions_count:  int   # nombre de sessions dans ce bloc
    mechanism:       str   # "LDP+Laplace+KAnon+TrimmedMoM"

    def validate(self) -> None:
        ec = Decimal(self.epsilon_client)
        es = Decimal(self.epsilon_server)
        et = Decimal(self.epsilon_total)
        em = Decimal(self.epsilon_max)
        if ec != EPSILON_CLIENT:
            raise EpsilonProofError(f"epsilon_client={ec} ≠ {EPSILON_CLIENT}")
        if es != EPSILON_SERVER:
            raise EpsilonProofError(f"epsilon_server={es} ≠ {EPSILON_SERVER}")
        if et > em:
            raise EpsilonProofError(f"epsilon_total={et} > epsilon_max={em} — kill-switch")
        if self.k_value < K_MIN:
            raise EpsilonProofError(f"K={self.k_value} < K_MIN={K_MIN}")
        if abs(self.wk_weight - WK) > 1e-9:
            raise EpsilonProofError(f"wK={self.wk_weight} ≠ {WK}")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EpsilonProof":
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# BLOC
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class VERABlock:
    """
    Bloc de la blockchain VERA.
    signal_agg = agrégat anonymisé. Jamais les valeurs brutes.
    """
    index:          int
    timestamp:      str            # ISO 8601 UTC
    epsilon_proof:  dict           # EpsilonProof.to_dict()
    signal_agg:     float          # trimmed median-of-means des contributions
    merkle_root:    str            # racine Merkle des hashes de contributions
    prev_hash:      str            # SHA256 du bloc précédent
    tsa_checkpoint: Optional[str]  # hash DER RFC3161 si checkpoint
    ed25519_sig:    str            # signature hex du bloc (sans ce champ)
    block_hash:     str            # SHA256 du bloc complet signé

    def _signable_bytes(self) -> bytes:
        """Canonicalisation déterministe pour signature."""
        d = {
            "index":         self.index,
            "timestamp":     self.timestamp,
            "epsilon_proof": self.epsilon_proof,
            "signal_agg":    self.signal_agg,
            "merkle_root":   self.merkle_root,
            "prev_hash":     self.prev_hash,
            "tsa_checkpoint": self.tsa_checkpoint,
        }
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def compute_hash(self) -> str:
        return _sha256(
            self._signable_bytes() + self.ed25519_sig.encode()
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "VERABlock":
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# GESTIONNAIRE DE CLÉS (léger, compatible vera_hardened_v5)
# ══════════════════════════════════════════════════════════════════════════════

class ChainKeyManager:
    """Clé Ed25519 persistante pour la signature des blocs."""

    def __init__(self, key_path: str):
        self._key_path = key_path
        self._pub_path = key_path + ".pub"
        self._private: Optional[object] = None
        self._public:  Optional[object] = None

    def load_or_generate(self) -> None:
        if os.path.exists(self._key_path) and HAS_CRYPTO:
            with open(self._key_path, "rb") as f:
                from cryptography.hazmat.primitives.serialization import load_pem_private_key
                self._private = load_pem_private_key(f.read(), password=None)
            self._public = self._private.public_key()
            logger.info("Clé chaîne chargée : %s", self._key_path)
        elif HAS_CRYPTO:
            self._private = Ed25519PrivateKey.generate()
            self._public  = self._private.public_key()
            with open(self._key_path, "wb") as f:
                f.write(self._private.private_bytes(
                    Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
                ))
            with open(self._pub_path, "wb") as f:
                f.write(self._public.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
            os.chmod(self._key_path, 0o600)
            logger.info("Nouvelle clé chaîne générée : %s", self._key_path)
        else:
            logger.warning("cryptography non disponible — signatures simulées")

    def sign(self, data: bytes) -> str:
        if HAS_CRYPTO and self._private:
            sig = self._private.sign(data)
            return sig.hex()
        return _sha256(data)   # fallback sans crypto

    def verify(self, data: bytes, sig_hex: str) -> bool:
        if HAS_CRYPTO and self._public:
            try:
                self._public.verify(bytes.fromhex(sig_hex), data)
                return True
            except Exception:
                return False
        return _sha256(data) == sig_hex   # fallback


# ══════════════════════════════════════════════════════════════════════════════
# ANCRAGE RFC3161
# ══════════════════════════════════════════════════════════════════════════════

def _tsa_anchor(block_hash: str, tsa_url: str = FREЕТSA_URL) -> Optional[str]:
    """
    Ancrage RFC3161 du hash de bloc.
    Retourne le SHA256 de la réponse DER, ou None si échec réseau.
    """
    try:
        data = bytes.fromhex(block_hash)[:20]   # 20 bytes pour SHA1 TSA
        nonce = int.from_bytes(os.urandom(8), "big")
        # TimeStampReq minimal ASN.1
        req = (
            b"\x30\x2e\x02\x01\x01"
            b"\x30\x21\x30\x09\x06\x05\x2b\x0e\x03\x02\x1a\x05\x00\x04\x14"
            + data
            + b"\x02\x08" + nonce.to_bytes(8, "big")
            + b"\x01\x01\xff"
        )
        request = urllib.request.Request(
            tsa_url, data=req,
            headers={"Content-Type": "application/timestamp-query"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as resp:
            der = resp.read()
        if not der or der[0] != 0x30:
            logger.warning("TSA réponse DER invalide")
            return None
        der_hash = _sha256(der)
        logger.info("Ancrage RFC3161 OK — der_sha256=%s... len=%d", der_hash[:16], len(der))
        return der_hash
    except Exception as e:
        logger.warning("Ancrage RFC3161 échoué : %s", e)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# VERA CHAIN
# ══════════════════════════════════════════════════════════════════════════════

class VERAChain:
    """
    Blockchain légère VERA — append-only, Ed25519 signé, ancrage RFC3161.

    Usage :
        chain = VERAChain()
        chain.load_or_init()
        chain.append_block(
            epsilon_proof=proof,
            contributions=["hash1", "hash2", ...],
            signal_agg=0.734,
        )
        chain.save()
    """

    def __init__(
        self,
        chain_path: str = os.path.join(_VERA_DIR, "vera_chain.json"),
        key_path:   str = os.path.join(_VERA_DIR, "vera_chain_key.pem"),
        tsa_url:    str = FREЕТSA_URL,
        checkpoint_interval: int = CHECKPOINT_INTERVAL,
    ):
        self._chain_path   = chain_path
        self._key_manager  = ChainKeyManager(key_path)
        self._tsa_url      = tsa_url
        self._checkpoint_n = checkpoint_interval
        self._blocks: List[VERABlock] = []
        self._lock = threading.Lock()

    # ── Init ──────────────────────────────────────────────────────────────────

    def load_or_init(self) -> None:
        self._key_manager.load_or_generate()
        if os.path.exists(self._chain_path):
            self._load()
            self._verify_chain_integrity()
            logger.info("Chaîne chargée : %d blocs", len(self._blocks))
        else:
            self._init_genesis()
            logger.info("Chaîne initialisée avec le bloc genesis")

    def _init_genesis(self) -> None:
        proof = EpsilonProof(
            epsilon_client  = str(EPSILON_CLIENT),
            epsilon_server  = str(EPSILON_SERVER),
            epsilon_total   = "0.0",
            epsilon_max     = str(EPSILON_TOTAL),
            k_value         = K_MIN,
            wk_weight       = WK,
            sessions_count  = 0,
            mechanism       = "GENESIS",
        )
        block = self._build_block(
            index        = 0,
            epsilon_proof= proof,
            contributions= ["genesis"],
            signal_agg   = 0.0,
            prev_hash    = GENESIS_PREV_HASH,
            tsa          = None,
        )
        self._blocks.append(block)
        self.save()

    # ── Ajout de bloc ─────────────────────────────────────────────────────────

    def append_block(
        self,
        epsilon_proof:  EpsilonProof,
        contributions:  List[str],   # liste de hashes anonymisés (jamais valeurs brutes)
        signal_agg:     float,
    ) -> VERABlock:
        """
        Ajoute un bloc à la chaîne.
        contributions = liste de SHA256 des signaux anonymisés.
        signal_agg    = résultat agrégé (trimmed median-of-means).
        """
        with self._lock:
            # Validation preuve epsilon
            epsilon_proof.validate()

            prev = self._blocks[-1]
            index = prev.index + 1

            # Checkpoint RFC3161 automatique tous les N blocs
            tsa = None
            if index % self._checkpoint_n == 0:
                logger.info("Checkpoint RFC3161 au bloc %d...", index)
                tsa = _tsa_anchor(prev.block_hash, self._tsa_url)

            block = self._build_block(
                index        = index,
                epsilon_proof= epsilon_proof,
                contributions= contributions,
                signal_agg   = signal_agg,
                prev_hash    = prev.block_hash,
                tsa          = tsa,
            )
            self._blocks.append(block)
            self.save()
            logger.info(
                "Bloc #%d ajouté — merkle=%s... hash=%s...",
                index, block.merkle_root[:12], block.block_hash[:12],
            )
            return block

    def _build_block(
        self,
        index:         int,
        epsilon_proof: EpsilonProof,
        contributions: List[str],
        signal_agg:    float,
        prev_hash:     str,
        tsa:           Optional[str],
    ) -> VERABlock:
        ts   = datetime.now(timezone.utc).isoformat()
        root = merkle_root(contributions)
        proof_dict = epsilon_proof.to_dict()

        # Données signables (sans ed25519_sig ni block_hash)
        signable = json.dumps({
            "index":          index,
            "timestamp":      ts,
            "epsilon_proof":  proof_dict,
            "signal_agg":     signal_agg,
            "merkle_root":    root,
            "prev_hash":      prev_hash,
            "tsa_checkpoint": tsa,
        }, sort_keys=True, separators=(",", ":")).encode()

        sig       = self._key_manager.sign(signable)
        blk_hash  = _sha256(signable + sig.encode())

        return VERABlock(
            index          = index,
            timestamp      = ts,
            epsilon_proof  = proof_dict,
            signal_agg     = signal_agg,
            merkle_root    = root,
            prev_hash      = prev_hash,
            tsa_checkpoint = tsa,
            ed25519_sig    = sig,
            block_hash     = blk_hash,
        )

    # ── Persistance ───────────────────────────────────────────────────────────

    def save(self) -> None:
        data = {
            "version":  CHAIN_VERSION,
            "length":   len(self._blocks),
            "head":     self._blocks[-1].block_hash if self._blocks else None,
            "blocks":   [b.to_dict() for b in self._blocks],
        }
        with open(self._chain_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        with open(self._chain_path) as f:
            data = json.load(f)
        self._blocks = [VERABlock.from_dict(b) for b in data["blocks"]]

    # ── Vérification ──────────────────────────────────────────────────────────

    def _verify_chain_integrity(self) -> None:
        """Vérifie la cohérence de toute la chaîne au chargement."""
        for i, block in enumerate(self._blocks):
            # prev_hash
            if i == 0:
                if block.prev_hash != GENESIS_PREV_HASH:
                    raise ChainIntegrityError(f"Bloc 0 : prev_hash invalide")
            else:
                expected = self._blocks[i - 1].block_hash
                if block.prev_hash != expected:
                    raise ChainIntegrityError(
                        f"Bloc {i} : prev_hash={block.prev_hash[:12]}... "
                        f"≠ attendu={expected[:12]}..."
                    )
            # signature
            signable = block._signable_bytes()
            if not self._key_manager.verify(signable, block.ed25519_sig):
                raise ChainSignatureError(f"Bloc {i} : signature Ed25519 invalide")
            # block_hash
            expected_hash = block.compute_hash()
            if block.block_hash != expected_hash:
                raise ChainIntegrityError(
                    f"Bloc {i} : block_hash={block.block_hash[:12]}... "
                    f"≠ calculé={expected_hash[:12]}..."
                )
        logger.info("Intégrité chaîne OK — %d blocs vérifiés", len(self._blocks))

    def verify_independent(self, chain_path: str) -> dict:
        """
        Vérification autonome d'un fichier chaîne.
        Utilisable par un auditeur CNIL sans accès au système vivant.
        """
        results = {"valid": True, "blocks_checked": 0, "errors": []}
        try:
            with open(chain_path) as f:
                data = json.load(f)
            blocks = [VERABlock.from_dict(b) for b in data["blocks"]]

            for i, block in enumerate(blocks):
                # prev_hash
                if i == 0:
                    if block.prev_hash != GENESIS_PREV_HASH:
                        results["errors"].append(f"Bloc 0 : prev_hash genesis invalide")
                        results["valid"] = False
                else:
                    if block.prev_hash != blocks[i-1].block_hash:
                        results["errors"].append(f"Bloc {i} : rupture de chaîne prev_hash")
                        results["valid"] = False

                # block_hash
                expected = block.compute_hash()
                if block.block_hash != expected:
                    results["errors"].append(f"Bloc {i} : block_hash corrompu")
                    results["valid"] = False

                # epsilon_proof
                try:
                    EpsilonProof.from_dict(block.epsilon_proof).validate()
                except EpsilonProofError as e:
                    if block.index > 0:   # genesis exempt
                        results["errors"].append(f"Bloc {i} : epsilon_proof invalide — {e}")
                        results["valid"] = False

                results["blocks_checked"] += 1

            results["head"] = blocks[-1].block_hash if blocks else None
            results["length"] = len(blocks)
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Erreur lecture : {e}")

        return results

    # ── Stats ─────────────────────────────────────────────────────────────────

    @property
    def length(self) -> int:
        return len(self._blocks)

    @property
    def head(self) -> Optional[VERABlock]:
        return self._blocks[-1] if self._blocks else None

    def summary(self) -> dict:
        if not self._blocks:
            return {"length": 0}
        head = self._blocks[-1]
        checkpoints = sum(1 for b in self._blocks if b.tsa_checkpoint)
        return {
            "version":         CHAIN_VERSION,
            "length":          len(self._blocks),
            "head_hash":       head.block_hash[:16] + "...",
            "head_index":      head.index,
            "head_timestamp":  head.timestamp,
            "tsa_checkpoints": checkpoints,
            "chain_path":      self._chain_path,
        }


# ══════════════════════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ══════════════════════════════════════════════════════════════════════════════

def run_chain_tests(test_dir: str = _VERA_DIR) -> None:
    print("\n" + "═" * 60)
    print("VERA Chain v1.0 — TESTS")
    print("═" * 60)
    passed = 0
    failed = 0

    def ok(name):
        nonlocal passed; passed += 1
        print(f"  ✓ {name}")

    def fail(name, err):
        nonlocal failed; failed += 1
        print(f"  ✗ {name} — {err}")

    chain_path = os.path.join(test_dir, "test_chain.json")
    key_path   = os.path.join(test_dir, "test_chain_key.pem")

    # Nettoyer les fichiers de test précédents
    for p in [chain_path, key_path, key_path + ".pub"]:
        if os.path.exists(p): os.remove(p)

    # ── Merkle ────────────────────────────────────────────────────────────────
    try:
        r1 = merkle_root(["a", "b", "c", "d"])
        r2 = merkle_root(["a", "b", "c", "d"])
        assert r1 == r2
        ok("Merkle : déterministe")
    except Exception as e:
        fail("Merkle : déterministe", e)

    try:
        r1 = merkle_root(["a", "b"])
        r2 = merkle_root(["a", "c"])
        assert r1 != r2
        ok("Merkle : sensible au contenu")
    except Exception as e:
        fail("Merkle : sensible au contenu", e)

    try:
        r = merkle_root([])
        assert r == _sha256(b"empty")
        ok("Merkle : liste vide → hash empty")
    except Exception as e:
        fail("Merkle : liste vide", e)

    # ── EpsilonProof ──────────────────────────────────────────────────────────
    try:
        proof = EpsilonProof("1.0","0.5","1.0","1.5",100,0.3,5,"LDP+Laplace")
        proof.validate()
        ok("EpsilonProof : valide → OK")
    except Exception as e:
        fail("EpsilonProof : valide", e)

    try:
        bad = EpsilonProof("0.8","0.5","1.0","1.5",100,0.3,5,"LDP")
        try:
            bad.validate()
            fail("EpsilonProof : epsilon_client invalide", "aucune exception")
        except EpsilonProofError:
            ok("EpsilonProof : epsilon_client invalide → EpsilonProofError")
    except Exception as e:
        fail("EpsilonProof : epsilon_client invalide", e)

    try:
        bad = EpsilonProof("1.0","0.5","1.6","1.5",100,0.3,5,"LDP")
        try:
            bad.validate()
            fail("EpsilonProof : epsilon_total > max", "aucune exception")
        except EpsilonProofError:
            ok("EpsilonProof : epsilon_total > max → EpsilonProofError")
    except Exception as e:
        fail("EpsilonProof : epsilon_total > max", e)

    # ── Chaîne ────────────────────────────────────────────────────────────────
    try:
        chain = VERAChain(chain_path=chain_path, key_path=key_path, tsa_url="")
        chain.load_or_init()
        assert chain.length == 1   # genesis
        assert chain._blocks[0].index == 0
        ok("Chaîne : genesis créé")
    except Exception as e:
        fail("Chaîne : genesis", e)

    try:
        proof = EpsilonProof("1.0","0.5","0.5","1.5",150,0.3,3,"LDP+Laplace+KAnon")
        contribs = [_sha256(f"user_{i}".encode()) for i in range(5)]
        block = chain.append_block(proof, contribs, signal_agg=0.742)
        assert block.index == 1
        assert block.prev_hash == chain._blocks[0].block_hash
        assert block.merkle_root == merkle_root(contribs)
        ok("Chaîne : bloc #1 ajouté avec prev_hash correct")
    except Exception as e:
        fail("Chaîne : bloc #1", e)

    try:
        proof2 = EpsilonProof("1.0","0.5","1.0","1.5",200,0.3,4,"LDP+Laplace+KAnon")
        contribs2 = [_sha256(f"user2_{i}".encode()) for i in range(3)]
        b2 = chain.append_block(proof2, contribs2, signal_agg=0.651)
        assert b2.index == 2
        ok("Chaîne : bloc #2 ajouté")
    except Exception as e:
        fail("Chaîne : bloc #2", e)

    # ── Intégrité ─────────────────────────────────────────────────────────────
    try:
        chain._verify_chain_integrity()
        ok("Intégrité : chaîne 3 blocs → OK")
    except Exception as e:
        fail("Intégrité : chaîne 3 blocs", e)

    # ── Vérification indépendante ─────────────────────────────────────────────
    try:
        result = chain.verify_independent(chain_path)
        assert result["valid"] is True
        assert result["blocks_checked"] == 3
        ok(f"Vérification indépendante : {result['blocks_checked']} blocs valides")
    except Exception as e:
        fail("Vérification indépendante", e)

    # ── Détection de falsification ────────────────────────────────────────────
    try:
        with open(chain_path) as f:
            data = json.load(f)
        # Falsifier le signal_agg du bloc 1
        data["blocks"][1]["signal_agg"] = 999.0
        tampered_path = chain_path + ".tampered"
        with open(tampered_path, "w") as f:
            json.dump(data, f)
        result = chain.verify_independent(tampered_path)
        assert result["valid"] is False
        os.remove(tampered_path)
        ok("Détection falsification : signal_agg altéré → invalide")
    except Exception as e:
        fail("Détection falsification", e)

    # ── Persistance (reload) ──────────────────────────────────────────────────
    try:
        chain2 = VERAChain(chain_path=chain_path, key_path=key_path, tsa_url="")
        chain2.load_or_init()
        assert chain2.length == 3
        assert chain2.head.block_hash == chain.head.block_hash
        ok("Persistance : rechargement 3 blocs → head identique")
    except Exception as e:
        fail("Persistance : rechargement", e)

    # ── Résumé ────────────────────────────────────────────────────────────────
    try:
        s = chain.summary()
        assert s["length"] == 3
        ok(f"Résumé : {s}")
    except Exception as e:
        fail("Résumé", e)

    # ── Nettoyage ─────────────────────────────────────────────────────────────
    for p in [chain_path, key_path, key_path + ".pub"]:
        if os.path.exists(p): os.remove(p)

    print("─" * 60)
    print(f"  Résultat : {passed} passés / {passed + failed} total")
    if failed == 0:
        print("  ✓ BLOC 2 VALIDÉ — vera_chain.py prêt pour Termux")
    else:
        print(f"  ✗ {failed} test(s) échoué(s)")
    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERA Chain — blockchain légère")
    parser.add_argument("--verify", metavar="CHAIN_JSON",
                        help="Vérification indépendante d'un fichier chaîne")
    parser.add_argument("--summary", action="store_true",
                        help="Afficher le résumé de la chaîne active")
    parser.add_argument("--test", action="store_true", default=True,
                        help="Lancer les tests (défaut)")
    args = parser.parse_args()

    if args.verify:
        chain = VERAChain()
        chain._key_manager.load_or_generate()
        result = chain.verify_independent(args.verify)
        print(json.dumps(result, indent=2))
    elif args.summary:
        chain = VERAChain()
        chain.load_or_init()
        print(json.dumps(chain.summary(), indent=2))
    else:
        run_chain_tests()
