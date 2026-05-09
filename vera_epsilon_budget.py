"""
VERA Epsilon Budget — vera_epsilon_budget.py
=============================================
Gestion du budget epsilon sur le temps long.

Problème résolu : la composition DP statique (T1-T5) prouve
epsilon_total ≤ 1.5 pour une session. Mais sur 30 jours
d'analyses quotidiennes, le budget s'accumule sans contrôle.

Ce module :
  - Suit l'epsilon cumulé sur une fenêtre temporelle
  - Déclenche le kill-switch si dépassement
  - Réinitialise le budget à la fin de chaque fenêtre
  - Persiste l'état entre redémarrages

Usage :
    budget = VERAEpsilonBudget(window_hours=24, epsilon_max=1.5)
    budget.consume(0.5, session_id="abc")   # OK
    budget.consume(1.0, session_id="def")   # OK — total=1.5
    budget.consume(0.1, session_id="ghi")   # VERAKillSwitch

    python3 vera_epsilon_budget.py --test
    python3 vera_epsilon_budget.py --status
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

_HOME     = os.path.expanduser("~")
_VERA_DIR = os.path.join(_HOME, "vera")
os.makedirs(_VERA_DIR, exist_ok=True)

# Invariants
EPSILON_MAX     = Decimal("1.5")
EPSILON_CLIENT  = Decimal("1.0")
EPSILON_SERVER  = Decimal("0.5")
DEFAULT_WINDOW  = 24   # heures


class VERAKillSwitch(Exception):
    """Budget epsilon épuisé — pipeline arrêté."""


# ══════════════════════════════════════════════════════════════════════════════
# ENTRÉE DE CONSOMMATION
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class BudgetEntry:
    session_id:  str
    epsilon:     str    # Decimal sérialisé
    timestamp:   str    # ISO 8601 UTC
    cumul:       str    # epsilon cumulé après cette consommation
    window_id:   str    # identifiant de la fenêtre (ex: "2026-05-09")

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "epsilon":    self.epsilon,
            "timestamp":  self.timestamp,
            "cumul":      self.cumul,
            "window_id":  self.window_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BudgetEntry":
        return cls(**d)


# ══════════════════════════════════════════════════════════════════════════════
# BUDGET EPSILON DYNAMIQUE
# ══════════════════════════════════════════════════════════════════════════════

class VERAEpsilonBudget:
    """
    Compteur de budget epsilon avec fenêtre glissante.

    Garantit que epsilon_total ≤ epsilon_max sur toute fenêtre
    de window_hours heures. Réinitialisation automatique en fin
    de fenêtre. Persistance sur disque entre redémarrages.
    """

    def __init__(
        self,
        window_hours: float = DEFAULT_WINDOW,
        epsilon_max:  Decimal = EPSILON_MAX,
        persist_path: Optional[str] = None,
    ):
        self._window_seconds = window_hours * 3600
        self._epsilon_max    = epsilon_max
        self._persist_path   = persist_path or os.path.join(
            _VERA_DIR, "vera_epsilon_budget.json"
        )
        self._lock    = threading.Lock()
        self._entries: List[BudgetEntry] = []
        self._load()

    # ── Persistance ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if os.path.exists(self._persist_path):
            try:
                with open(self._persist_path) as f:
                    data = json.load(f)
                self._entries = [BudgetEntry.from_dict(e) for e in data.get("entries", [])]
                self._evict()
            except Exception:
                self._entries = []

    def _save(self) -> None:
        data = {
            "version":     "1.0",
            "epsilon_max": str(self._epsilon_max),
            "window_h":    self._window_seconds / 3600,
            "saved_at":    datetime.now(timezone.utc).isoformat(),
            "entries":     [e.to_dict() for e in self._entries],
        }
        with open(self._persist_path, "w") as f:
            json.dump(data, f, indent=2)

    # ── Nettoyage des entrées hors fenêtre ────────────────────────────────────

    def _evict(self) -> None:
        """Supprime les entrées plus anciennes que la fenêtre."""
        cutoff = time.time() - self._window_seconds
        self._entries = [
            e for e in self._entries
            if self._entry_timestamp(e) >= cutoff
        ]

    @staticmethod
    def _entry_timestamp(e: BudgetEntry) -> float:
        try:
            dt = datetime.fromisoformat(e.timestamp)
            return dt.timestamp()
        except Exception:
            return 0.0

    # ── Budget courant ────────────────────────────────────────────────────────

    def _current_cumul(self) -> Decimal:
        self._evict()
        return sum(Decimal(e.epsilon) for e in self._entries)

    def _window_id(self) -> str:
        """Identifiant de la fenêtre courante (ex: date du jour)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ── Consommation ─────────────────────────────────────────────────────────

    def consume(self, epsilon: Decimal, session_id: str) -> Decimal:
        """
        Consomme epsilon du budget.
        Lève VERAKillSwitch si dépassement.
        Retourne l'epsilon cumulé après consommation.
        """
        epsilon = Decimal(str(epsilon))

        with self._lock:
            self._evict()
            current = self._current_cumul()
            projected = current + epsilon

            if projected > self._epsilon_max:
                raise VERAKillSwitch(
                    f"KILL-SWITCH budget epsilon : "
                    f"cumulé={current} + demande={epsilon} = {projected} "
                    f"> max={self._epsilon_max}. "
                    f"Fenêtre : {self._window_seconds/3600:.0f}h. "
                    f"Réinitialisation dans "
                    f"{self._time_to_reset():.0f}s."
                )

            entry = BudgetEntry(
                session_id = session_id,
                epsilon    = str(epsilon),
                timestamp  = datetime.now(timezone.utc).isoformat(),
                cumul      = str(projected),
                window_id  = self._window_id(),
            )
            self._entries.append(entry)
            self._save()
            return projected

    def _time_to_reset(self) -> float:
        """Secondes avant la prochaine réinitialisation."""
        if not self._entries:
            return 0.0
        oldest = min(self._entry_timestamp(e) for e in self._entries)
        reset_at = oldest + self._window_seconds
        return max(0.0, reset_at - time.time())

    # ── Propriétés ────────────────────────────────────────────────────────────

    @property
    def epsilon_spent(self) -> Decimal:
        with self._lock:
            return self._current_cumul()

    @property
    def epsilon_remaining(self) -> Decimal:
        return self._epsilon_max - self.epsilon_spent

    @property
    def is_exhausted(self) -> bool:
        return self.epsilon_spent >= self._epsilon_max

    def status(self) -> dict:
        with self._lock:
            self._evict()
            current = self._current_cumul()
            return {
                "epsilon_spent":     float(current),
                "epsilon_remaining": float(self._epsilon_max - current),
                "epsilon_max":       float(self._epsilon_max),
                "pct_used":          float(current / self._epsilon_max * 100),
                "entries_in_window": len(self._entries),
                "window_hours":      self._window_seconds / 3600,
                "time_to_reset_s":   round(self._time_to_reset(), 1),
                "is_exhausted":      current >= self._epsilon_max,
                "window_id":         self._window_id(),
            }

    def reset(self) -> None:
        """Réinitialisation manuelle — opérateur uniquement."""
        with self._lock:
            self._entries = []
            self._save()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ══════════════════════════════════════════════════════════════════════════════

def run_budget_tests() -> None:
    print("\n" + "═" * 60)
    print("VERA Epsilon Budget — TESTS")
    print("═" * 60)
    passed = 0
    failed = 0

    test_path = os.path.join(_VERA_DIR, "test_budget.json")

    def ok(name):
        nonlocal passed; passed += 1
        print(f"  ✓ {name}")

    def fail(name, err):
        nonlocal failed; failed += 1
        print(f"  ✗ {name} — {err}")

    def fresh():
        if os.path.exists(test_path):
            os.remove(test_path)
        return VERAEpsilonBudget(
            window_hours=1.0,
            epsilon_max=EPSILON_MAX,
            persist_path=test_path
        )

    # ── Consommation normale ──────────────────────────────────────────────────
    try:
        b = fresh()
        c1 = b.consume(EPSILON_CLIENT, "sess-1")
        assert c1 == EPSILON_CLIENT
        ok(f"Consommation epsilon_client={EPSILON_CLIENT} → cumul={c1}")
    except Exception as e:
        fail("Consommation normale", e)

    # ── Deuxième consommation ─────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(EPSILON_CLIENT, "sess-1")
        c2 = b.consume(EPSILON_SERVER, "sess-2")
        assert c2 == EPSILON_MAX
        ok(f"Double consommation → cumul={c2} = epsilon_max")
    except Exception as e:
        fail("Double consommation", e)

    # ── Kill-switch ───────────────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(EPSILON_CLIENT, "sess-1")
        b.consume(EPSILON_SERVER, "sess-2")
        try:
            b.consume(Decimal("0.1"), "sess-3")
            fail("Kill-switch non déclenché", "aucune exception")
        except VERAKillSwitch:
            ok("Kill-switch déclenché : 1.5 + 0.1 > 1.5")
    except Exception as e:
        fail("Kill-switch", e)

    # ── Epsilon restant ───────────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(Decimal("0.5"), "sess-1")
        remaining = b.epsilon_remaining
        assert remaining == Decimal("1.0")
        ok(f"Epsilon restant : {remaining} après consommation 0.5")
    except Exception as e:
        fail("Epsilon restant", e)

    # ── Persistance ───────────────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(Decimal("0.8"), "sess-persist")
        # Recharger depuis disque
        b2 = VERAEpsilonBudget(
            window_hours=1.0,
            epsilon_max=EPSILON_MAX,
            persist_path=test_path
        )
        assert b2.epsilon_spent == Decimal("0.8")
        ok(f"Persistance : rechargé depuis disque, spent={b2.epsilon_spent}")
    except Exception as e:
        fail("Persistance", e)

    # ── Réinitialisation fenêtre ──────────────────────────────────────────────
    try:
        # Fenêtre de 0.001h = 3.6 secondes
        if os.path.exists(test_path): os.remove(test_path)
        b = VERAEpsilonBudget(
            window_hours=0.001,
            epsilon_max=EPSILON_MAX,
            persist_path=test_path
        )
        b.consume(Decimal("1.0"), "sess-window")
        assert b.epsilon_spent == Decimal("1.0")
        time.sleep(4)   # Attendre expiration fenêtre
        b._evict()
        assert b.epsilon_spent == Decimal("0")
        ok("Fenêtre expirée : budget réinitialisé automatiquement")
    except Exception as e:
        fail("Réinitialisation fenêtre", e)

    # ── Status ────────────────────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(Decimal("0.5"), "sess-status")
        s = b.status()
        assert s["epsilon_spent"] == 0.5
        assert s["pct_used"] == pytest_approx(33.33, abs=0.1) if False else abs(s["pct_used"] - 33.33) < 0.1
        assert not s["is_exhausted"]
        ok(f"Status : spent={s['epsilon_spent']}, pct={s['pct_used']:.1f}%")
    except Exception as e:
        fail("Status", e)

    # ── Reset manuel ─────────────────────────────────────────────────────────
    try:
        b = fresh()
        b.consume(Decimal("1.2"), "sess-reset")
        assert b.epsilon_spent == Decimal("1.2")
        b.reset()
        assert b.epsilon_spent == Decimal("0")
        ok("Reset manuel : budget remis à zéro")
    except Exception as e:
        fail("Reset manuel", e)

    # ── Multi-sessions thread-safe ────────────────────────────────────────────
    try:
        b = fresh()
        errors = []

        def worker(i):
            try:
                b.consume(Decimal("0.01"), f"thread-{i}")
            except VERAKillSwitch:
                pass
            except Exception as ex:
                errors.append(ex)

        import threading as _t
        threads = [_t.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert not errors, f"Erreurs thread : {errors}"
        assert b.epsilon_spent <= EPSILON_MAX
        ok(f"Thread-safety : 20 threads, spent={b.epsilon_spent}, pas de violation")
    except Exception as e:
        fail("Thread-safety", e)

    # Nettoyage
    if os.path.exists(test_path):
        os.remove(test_path)

    print("─" * 60)
    print(f"  Résultat : {passed} passés / {passed + failed} total")
    if failed == 0:
        print("  ✓ VERA Epsilon Budget VALIDÉ — composition temporelle résolue")
    else:
        print(f"  ✗ {failed} test(s) échoué(s)")
    print("═" * 60 + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERA Epsilon Budget")
    parser.add_argument("--test",   action="store_true", help="Tests intégrés")
    parser.add_argument("--status", action="store_true", help="Afficher le statut du budget")
    parser.add_argument("--reset",  action="store_true", help="Réinitialiser le budget (opérateur)")
    args = parser.parse_args()

    if args.test:
        run_budget_tests()
    elif args.status:
        if os.path.exists(test_path): os.remove(test_path)
        b = VERAEpsilonBudget()
        s = b.status()
        print(json.dumps(s, indent=2))
    elif args.reset:
        if os.path.exists(test_path): os.remove(test_path)
        b = VERAEpsilonBudget()
        b.reset()
        print("Budget réinitialisé.")
    else:
        run_budget_tests()
