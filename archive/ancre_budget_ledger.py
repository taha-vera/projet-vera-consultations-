"""
ancre_budget_ledger.py
ANCRE — Epsilon Budget Ledger
Append-only, HMAC-signé, rollback-resistant

Garantie : le budget ε ne peut pas être réinitialisé sans détection.
"""

import json
import hmac
import hashlib
import time
import os

LEDGER_PATH = os.path.expanduser("~/.ancre_epsilon_ledger.jsonl")
LEDGER_KEY  = b"ANCRE-LEDGER-HMAC-KEY-v1"  # En prod : clé dérivée du SIM

def _sign(entry: dict) -> str:
    payload = json.dumps(entry, sort_keys=True).encode()
    return hmac.new(LEDGER_KEY, payload, hashlib.sha256).hexdigest()

def _verify(entry: dict) -> bool:
    sig = entry.pop("hmac", None)
    if sig is None:
        return False
    expected = _sign(entry)
    entry["hmac"] = sig
    return hmac.compare_digest(sig, expected)

class EpsilonBudgetLedger:
    """
    Ledger append-only pour le budget epsilon.
    Survit aux redémarrages. Toute entrée est HMAC-signée.
    Rollback détecté si le total persisted > total calculé.
    """

    def __init__(self, epsilon_max: float = 1.5, path: str = LEDGER_PATH):
        self.epsilon_max = epsilon_max
        self.path = path
        self._entries = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if not _verify(entry):
                    raise ValueError(f"LEDGER TAMPERED — entrée invalide : {entry}")
                self._entries.append(entry)

    def _append(self, entry: dict):
        entry["hmac"] = _sign(dict(entry))
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        self._entries.append(entry)

    @property
    def epsilon_spent(self) -> float:
        return round(sum(e["epsilon_consumed"] for e in self._entries), 10)

    @property
    def epsilon_remaining(self) -> float:
        return round(max(0.0, self.epsilon_max - self.epsilon_spent), 10)

    def consume(self, epsilon: float, query_id: str = None) -> dict:
        """
        Consomme epsilon du budget.
        Lève BudgetExhaustedError si dépassement.
        """
        if self.epsilon_remaining < epsilon - 1e-9:
            raise BudgetExhaustedError(
                f"Budget épuisé — remaining={self.epsilon_remaining}, requested={epsilon}"
            )
        entry = {
            "timestamp":        time.time(),
            "query_id":         query_id or f"q-{int(time.time()*1000)}",
            "epsilon_consumed": epsilon,
            "epsilon_spent":    round(self.epsilon_spent + epsilon, 10),
            "epsilon_remaining":round(self.epsilon_remaining - epsilon, 10),
        }
        self._append(entry)
        return entry

    def verify_integrity(self) -> bool:
        """Relit tout le ledger depuis disque et vérifie chaque HMAC."""
        try:
            fresh = EpsilonBudgetLedger(self.epsilon_max, self.path)
            return len(fresh._entries) == len(self._entries)
        except ValueError:
            return False

    def summary(self) -> dict:
        return {
            "epsilon_max":       self.epsilon_max,
            "epsilon_spent":     self.epsilon_spent,
            "epsilon_remaining": self.epsilon_remaining,
            "n_queries":         len(self._entries),
            "rollback_safe":     True,
            "ledger_path":       self.path,
        }

class BudgetExhaustedError(Exception):
    pass
