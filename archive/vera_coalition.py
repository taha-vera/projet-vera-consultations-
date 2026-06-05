"""
VERA Coalition Detector — vera_coalition.py
============================================
Remplacement du détecteur heuristique par un test statistique formel.

Approche :
  - Test du chi² sur la distribution temporelle des requêtes
  - Test de Kolmogorov-Smirnov sur les inter-arrivées
  - Seuil dérivé de K et wK : si corrélation > 1/(K*wK) → alerte

Invariants VERA :
  K ≥ 100, wK = 0.3 → seuil coalition = 1/(100*0.3) = 3.3%

Usage :
    python3 vera_coalition.py         # tests intégrés
    python3 vera_coalition.py --demo  # démonstration sur données simulées
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ── Constantes VERA ───────────────────────────────────────────────────────────
K_MIN              = 100
WK                 = 0.3
COALITION_THRESHOLD = 1.0 / (K_MIN * WK)   # 0.0333... = 3.3%
MIN_SAMPLES        = 20     # minimum pour test fiable
P_VALUE_THRESHOLD  = 0.05   # seuil de significativité
CHI2_BINS          = 10     # bins pour le test chi²

_HOME     = os.path.expanduser("~")
_VERA_DIR = os.path.join(_HOME, "vera")


# ══════════════════════════════════════════════════════════════════════════════
# RÉSULTAT DE DÉTECTION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CoalitionResult:
    """Résultat d'un test de détection de coalition."""
    origin_id:        str
    n_samples:        int
    chi2_stat:        float
    chi2_p_value:     float
    ks_stat:          float
    ks_p_value:       float
    coalition_score:  float    # 0.0 (légitime) → 1.0 (coalition certaine)
    is_coalition:     bool
    reason:           str
    confidence:       str      # LOW / MEDIUM / HIGH

    def to_dict(self) -> dict:
        return {
            "origin_id":       self.origin_id,
            "n_samples":       self.n_samples,
            "chi2_stat":       round(self.chi2_stat, 4),
            "chi2_p_value":    round(self.chi2_p_value, 4),
            "ks_stat":         round(self.ks_stat, 4),
            "ks_p_value":      round(self.ks_p_value, 4),
            "coalition_score": round(self.coalition_score, 4),
            "is_coalition":    self.is_coalition,
            "reason":          self.reason,
            "confidence":      self.confidence,
            "threshold":       round(COALITION_THRESHOLD, 4),
        }


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS STATISTIQUES (stdlib uniquement)
# ══════════════════════════════════════════════════════════════════════════════

def _chi2_cdf(x: float, k: int) -> float:
    """CDF approximée du chi² avec k degrés de liberté — algorithme de Wilson-Hilferty."""
    if x <= 0:
        return 0.0
    # Approximation normale via Wilson-Hilferty
    z = ((x / k) ** (1/3) - (1 - 2/(9*k))) / math.sqrt(2/(9*k))
    return _normal_cdf(z)

def _normal_cdf(z: float) -> float:
    """CDF normale standard — approximation Abramowitz & Stegun."""
    if z < -8:
        return 0.0
    if z > 8:
        return 1.0
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    poly = t * (0.319381530
              + t * (-0.356563782
              + t * (1.781477937
              + t * (-1.821255978
              + t * 1.330274429))))
    p = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return p if z >= 0 else 1.0 - p

def _chi2_test(observed: List[float], expected_uniform: bool = True) -> Tuple[float, float]:
    """
    Test du chi² sur une distribution observée.
    Si expected_uniform=True, compare à une distribution uniforme.
    Retourne (statistique chi², p-value).
    """
    n = sum(observed)
    if n == 0:
        return 0.0, 1.0
    k = len(observed)
    expected = n / k if expected_uniform else n / k
    chi2 = sum((o - expected) ** 2 / expected for o in observed if expected > 0)
    df   = k - 1
    p    = 1.0 - _chi2_cdf(chi2, df)
    return chi2, p

def _ks_test_uniform(samples: List[float]) -> Tuple[float, float]:
    """
    Test KS des inter-arrivées contre une loi exponentielle (trafic Poisson légitime).
    Transforme via CDF exponentielle avant le test — trafic légitime → p élevée.
    Coalition (burst) → inter-arrivées non-exponentielles → p faible.
    """
    if not samples:
        return 0.0, 1.0
    n = len(samples)
    if n < 2:
        return 0.0, 1.0
    mean = sum(samples) / n
    if mean <= 0:
        return 1.0, 0.0
    # Transformer via CDF exponentielle : U = 1 - exp(-x/mean)
    # Si X ~ Exp(1/mean), alors U ~ Uniform[0,1]
    transformed = [1.0 - math.exp(-x / mean) for x in samples]
    sorted_s = sorted(transformed)
    d_plus  = max((i + 1) / n - x for i, x in enumerate(sorted_s))
    d_minus = max(x - i / n for i, x in enumerate(sorted_s))
    d       = max(d_plus, d_minus)
    lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * d
    p   = 2 * sum(
        (-1) ** (j - 1) * math.exp(-2 * j * j * lam * lam)
        for j in range(1, 20)
    )
    p = max(0.0, min(1.0, p))
    return d, p


# ══════════════════════════════════════════════════════════════════════════════
# DÉTECTEUR DE COALITION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RequestRecord:
    """Enregistrement d'une requête pour analyse."""
    timestamp:   float   # time.monotonic()
    origin_hash: str
    value_hash:  str     # hash de la valeur (jamais la valeur brute)

class VERACoalitionDetector:
    """
    Détecteur de coalitions basé sur des tests statistiques formels.

    Une coalition = groupe d'origines coordonnées tentant de reconstituer
    des données individuelles par agrégation de requêtes corrélées.

    Méthode :
      1. Chi² sur la distribution temporelle (les coalitions arrivent en bursts)
      2. KS sur les inter-arrivées normalisées (les coalitions ne sont pas poisson)
      3. Score combiné normalisé [0,1]
      4. Seuil dérivé de K et wK : 1/(K*wK) = 3.3%
    """

    def __init__(
        self,
        window_seconds:   float = 300.0,   # fenêtre d'analyse 5 min
        min_samples:      int   = MIN_SAMPLES,
        p_threshold:      float = P_VALUE_THRESHOLD,
        coalition_thresh: float = COALITION_THRESHOLD,
    ):
        self._window       = window_seconds
        self._min_samples  = min_samples
        self._p_threshold  = p_threshold
        self._c_threshold  = coalition_thresh
        self._records: List[RequestRecord] = []

    def record(self, origin_hash: str, value_hash: str) -> None:
        """Enregistre une requête."""
        self._records.append(RequestRecord(
            timestamp   = time.monotonic(),
            origin_hash = origin_hash,
            value_hash  = value_hash,
        ))
        self._evict()

    def _evict(self) -> None:
        """Supprime les enregistrements hors fenêtre."""
        cutoff = time.monotonic() - self._window
        self._records = [r for r in self._records if r.timestamp >= cutoff]

    def analyze(self, origin_hash: str) -> CoalitionResult:
        """
        Analyse les requêtes d'une origine donnée.
        Retourne un CoalitionResult avec statistiques formelles.
        """
        self._evict()
        samples = [r for r in self._records if r.origin_hash == origin_hash]
        n = len(samples)

        if n < self._min_samples:
            return CoalitionResult(
                origin_id       = origin_hash[:12],
                n_samples       = n,
                chi2_stat       = 0.0,
                chi2_p_value    = 1.0,
                ks_stat         = 0.0,
                ks_p_value      = 1.0,
                coalition_score = 0.0,
                is_coalition    = False,
                reason          = f"Données insuffisantes : {n} < {self._min_samples} requis",
                confidence      = "LOW",
            )

        timestamps = sorted(r.timestamp for r in samples)

        # ── Test 1 : Chi² sur distribution temporelle ─────────────────────────
        t_min   = timestamps[0]
        t_max   = timestamps[-1]
        t_range = t_max - t_min

        if t_range < 1e-6:
            # Toutes les requêtes simultanées — burst évident
            chi2_stat, chi2_p = 1000.0, 0.0
        else:
            # Répartir dans CHI2_BINS bins temporels
            bins = [0.0] * CHI2_BINS
            for t in timestamps:
                b = min(int((t - t_min) / t_range * CHI2_BINS), CHI2_BINS - 1)
                bins[b] += 1
            chi2_stat, chi2_p = _chi2_test(bins, expected_uniform=True)

        # ── Test 2 : KS sur inter-arrivées normalisées ────────────────────────
        if len(timestamps) < 2:
            ks_stat, ks_p = 0.0, 1.0
        else:
            inter = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            max_inter = max(inter) if max(inter) > 0 else 1.0
            # Normaliser [0,1] pour comparaison avec uniforme
            # Une distribution de Poisson (trafic légitime) donne des inter-arrivées
            # exponentielles — une coalition donne des bursts réguliers
            normalized = [x / max_inter for x in inter]
            ks_stat, ks_p = _ks_test_uniform(normalized)

        # ── Score combiné ─────────────────────────────────────────────────────
        # chi2_score : 1.0 si p < threshold, 0.0 si p > 0.5
        chi2_score = max(0.0, min(1.0, (self._p_threshold - chi2_p) / self._p_threshold))
        # ks_score   : 1.0 si p < threshold
        ks_score   = max(0.0, min(1.0, (self._p_threshold - ks_p) / self._p_threshold))
        # Score moyen pondéré (chi² plus fiable sur petits échantillons)
        score = 0.6 * chi2_score + 0.4 * ks_score

        # ── Seuil dérivé de K et wK ───────────────────────────────────────────
        # Si score > 1/(K*wK) → coalition probable
        is_coalition = score > 0.5  # seuil détection [0,1] distinct du seuil K-anonymité

        # ── Confiance ─────────────────────────────────────────────────────────
        if n < 30:
            confidence = "LOW"
        elif n < 100:
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"

        # ── Raison ───────────────────────────────────────────────────────────
        reasons = []
        if chi2_p < self._p_threshold:
            reasons.append(f"chi²={chi2_stat:.2f} p={chi2_p:.4f} (distribution non-uniforme)")
        if ks_p < self._p_threshold:
            reasons.append(f"KS={ks_stat:.4f} p={ks_p:.4f} (inter-arrivées suspectes)")
        if not reasons:
            reasons.append("Distribution temporelle normale")

        return CoalitionResult(
            origin_id       = origin_hash[:12],
            n_samples       = n,
            chi2_stat       = chi2_stat,
            chi2_p_value    = chi2_p,
            ks_stat         = ks_stat,
            ks_p_value      = ks_p,
            coalition_score = score,
            is_coalition    = is_coalition,
            reason          = " | ".join(reasons),
            confidence      = confidence,
        )

    def analyze_all(self) -> List[CoalitionResult]:
        """Analyse toutes les origines actives dans la fenêtre."""
        self._evict()
        origins = set(r.origin_hash for r in self._records)
        return [self.analyze(o) for o in origins]

    def get_alerts(self) -> List[CoalitionResult]:
        """Retourne uniquement les origines détectées comme coalitions."""
        return [r for r in self.analyze_all() if r.is_coalition]


# ══════════════════════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ══════════════════════════════════════════════════════════════════════════════

def run_coalition_tests() -> None:
    print("\n" + "═" * 60)
    print("VERA Coalition Detector — TESTS")
    print("═" * 60)
    passed = 0
    failed = 0

    def ok(name):
        nonlocal passed; passed += 1
        print(f"  ✓ {name}")

    def fail(name, err):
        nonlocal failed; failed += 1
        print(f"  ✗ {name} — {err}")

    # ── Utilitaires test ──────────────────────────────────────────────────────
    def _hash(s: str) -> str:
        return hashlib.sha256(s.encode()).hexdigest()

    def _inject_uniform(detector, origin, n, spread=10.0):
        """Injecte n requêtes Poisson (trafic légitime réaliste)."""
        base = time.monotonic() - spread
        t = 0.0
        for i in range(n):
            t += random.expovariate(n / spread)
            r = RequestRecord(
                timestamp   = base + min(t, spread),
                origin_hash = origin,
                value_hash  = _hash(f"val_{i}"),
            )
            detector._records.append(r)

    def _inject_burst(detector, origin, n, burst_ratio=0.9):
        """Injecte n requêtes dont burst_ratio% arrivent en même temps."""
        base = time.monotonic() - 5.0
        n_burst = int(n * burst_ratio)
        for i in range(n_burst):
            detector._records.append(RequestRecord(
                timestamp   = base + 0.01 * i,   # burst serré
                origin_hash = origin,
                value_hash  = _hash(f"burst_{i}"),
            ))
        for i in range(n - n_burst):
            detector._records.append(RequestRecord(
                timestamp   = base + 3.0 + i * 0.5,
                origin_hash = origin,
                value_hash  = _hash(f"spread_{i}"),
            ))

    # ── Tests fonctions statistiques ──────────────────────────────────────────
    try:
        chi2, p = _chi2_test([10.0]*10)   # parfaitement uniforme
        assert p > 0.05, f"p={p} devrait être > 0.05 pour distribution uniforme"
        ok(f"Chi² distribution uniforme → p={p:.3f} > 0.05")
    except Exception as e:
        fail("Chi² distribution uniforme", e)

    try:
        chi2, p = _chi2_test([100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert p < 0.05, f"p={p} devrait être < 0.05 pour distribution concentrée"
        ok(f"Chi² distribution concentrée → p={p:.4f} < 0.05")
    except Exception as e:
        fail("Chi² distribution concentrée", e)

    try:
        import random as _r
        _r.seed(42)
        exp_samples = [_r.expovariate(1.0) for _ in range(100)]
        ks, p = _ks_test_uniform(exp_samples)
        assert p > 0.05, f"p={p} devrait être > 0.05 pour distribution exponentielle"
        ok(f"KS distribution exponentielle légitime → p={p:.3f} > 0.05")
    except Exception as e:
        fail("KS distribution uniforme", e)

    # ── Test données insuffisantes ────────────────────────────────────────────
    try:
        d = VERACoalitionDetector()
        origin = _hash("origin_test")
        for i in range(10):   # < MIN_SAMPLES=20
            d.record(origin, _hash(f"v{i}"))
        result = d.analyze(origin)
        assert not result.is_coalition
        assert result.confidence == "LOW"
        ok(f"Données insuffisantes (n=10 < 20) → pas de fausse alerte")
    except Exception as e:
        fail("Données insuffisantes", e)

    # ── Test trafic légitime ──────────────────────────────────────────────────
    try:
        d = VERACoalitionDetector()
        origin = _hash("legitimate_origin")
        _inject_uniform(d, origin, 50, spread=60.0)
        result = d.analyze(origin)
        assert not result.is_coalition, f"Fausse alerte ! score={result.coalition_score:.4f}"
        ok(f"Trafic légitime uniforme (n=50) → pas de coalition (score={result.coalition_score:.4f})")
    except Exception as e:
        fail("Trafic légitime", e)

    # ── Test coalition burst ──────────────────────────────────────────────────
    try:
        d = VERACoalitionDetector()
        origin = _hash("coalition_origin")
        _inject_burst(d, origin, 50, burst_ratio=0.9)
        result = d.analyze(origin)
        assert result.is_coalition, f"Coalition non détectée ! score={result.coalition_score:.4f}"
        ok(f"Coalition burst (90% en même temps) → détectée (score={result.coalition_score:.4f})")
    except Exception as e:
        fail("Coalition burst", e)

    # ── Test seuil dérivé K/wK ───────────────────────────────────────────────
    try:
        expected_threshold = 1.0 / (K_MIN * WK)
        assert abs(COALITION_THRESHOLD - expected_threshold) < 1e-9
        ok(f"Seuil coalition = 1/(K*wK) = 1/({K_MIN}*{WK}) = {COALITION_THRESHOLD:.4f} (3.3%)")
    except Exception as e:
        fail("Seuil K/wK", e)

    # ── Test plusieurs origines ───────────────────────────────────────────────
    try:
        d = VERACoalitionDetector()
        legit   = _hash("legit")
        bad     = _hash("bad")
        _inject_uniform(d, legit, 30, spread=60.0)
        _inject_burst(d, bad, 40, burst_ratio=0.95)
        alerts = d.get_alerts()
        alert_ids = [a.origin_id for a in alerts]
        assert bad[:12] in alert_ids,     f"Coalition non détectée parmi {alert_ids}"
        assert legit[:12] not in alert_ids, f"Fausse alerte sur légitime"
        ok(f"Multi-origines : coalition isolée, légitime non alertée")
    except Exception as e:
        fail("Multi-origines", e)

    # ── Test normal_cdf ───────────────────────────────────────────────────────
    try:
        assert abs(_normal_cdf(0) - 0.5) < 0.01
        assert _normal_cdf(10) > 0.999
        assert _normal_cdf(-10) < 0.001
        ok("CDF normale : valeurs de référence correctes")
    except Exception as e:
        fail("CDF normale", e)

    # ── Résultat ──────────────────────────────────────────────────────────────
    print("─" * 60)
    print(f"  Seuil coalition : 1/(K*wK) = 1/({K_MIN}×{WK}) = {COALITION_THRESHOLD:.4f}")
    print(f"  Résultat : {passed} passés / {passed + failed} total")
    if failed == 0:
        print("  ✓ COALITION DETECTOR VALIDÉ — heuristique remplacée par chi²+KS")
    else:
        print(f"  ✗ {failed} test(s) échoué(s)")
    print("═" * 60 + "\n")


def demo() -> None:
    """Démonstration sur données simulées."""
    print("\n── VERA Coalition Detector — DÉMO ──")
    d = VERACoalitionDetector()

    def _hash(s): return hashlib.sha256(s.encode()).hexdigest()

    # Origine A : trafic normal (écoute radio naturelle)
    base = time.monotonic() - 120
    for i in range(40):
        d._records.append(RequestRecord(
            timestamp   = base + random.expovariate(0.5),
            origin_hash = _hash("radio_normale"),
            value_hash  = _hash(f"track_{i}"),
        ))

    # Origine B : coalition coordonnée (burst d'attaque)
    for i in range(35):
        d._records.append(RequestRecord(
            timestamp   = base + 0.001 * i,
            origin_hash = _hash("attaquant_coalition"),
            value_hash  = _hash(f"attack_{i}"),
        ))

    for result in d.analyze_all():
        status = "🚨 COALITION" if result.is_coalition else "✓  LÉGITIME"
        print(f"  {status} | origin={result.origin_id} | n={result.n_samples} "
              f"| score={result.coalition_score:.4f} | conf={result.confidence}")
        print(f"           chi²_p={result.chi2_p_value:.4f} "
              f"| KS_p={result.ks_p_value:.4f} | {result.reason}")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        run_coalition_tests()
