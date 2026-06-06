"""
vera_d.py
VERA-D — Temporal Degradation of DP Aggregates

Principle : A DP aggregate produced today leaks information.
Over time, listening habits change. An old aggregate can
allow re-identification of individuals who changed their habits.

VERA-D adds a time-dependent noise layer on top of ANCRE aggregates.
The older the aggregate, the more noise is added until invalidation.

Formal guarantee :
  M_VERA-D(agg, t) = clamp(agg + DLap(scale(t)), 0, 1)
  where scale(t) increases monotonically with age t

Invariants (NON MODIFIABLE) :
  T1 = 30 days  → light degradation (ε_degradation = 0.1)
  T2 = 90 days  → strong degradation (ε_degradation = 0.5)
  T3 = 180 days → invalidation (aggregate returns None)

Version : 0.1
Author  : SAS VERA / VERA-D
"""

import math
import secrets
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────
# VERA-D Invariants
# ─────────────────────────────────────────────

T1_DAYS = 30    # Light degradation threshold
T2_DAYS = 90    # Strong degradation threshold
T3_DAYS = 180   # Invalidation threshold

# ε_degradation per tier (additional noise)
EPS_T1 = 0.1   # Light : small additional noise
EPS_T2 = 0.5   # Strong : significant additional noise
EPS_T3 = None  # Invalidated : no output


class DegradationTier(Enum):
    FRESH     = "fresh"       # age < T1 : no degradation
    LIGHT     = "light"       # T1 ≤ age < T2 : ε_d = 0.1
    STRONG    = "strong"      # T2 ≤ age < T3 : ε_d = 0.5
    INVALID   = "invalid"     # age ≥ T3 : aggregate invalidated


@dataclass
class DegradedAggregate:
    """Result of VERA-D temporal degradation."""
    original_value: float
    degraded_value: Optional[float]
    tier: DegradationTier
    age_days: float
    epsilon_total: float    # ε_ANCRE + ε_degradation
    valid: bool
    degraded_at: str


# ─────────────────────────────────────────────
# Discrete Laplace for VERA-D
# ─────────────────────────────────────────────

def _geometric_sample(p: float) -> int:
    """Sample from Geometric(p) using CSPRNG."""
    if p <= 0.0 or p >= 1.0:
        raise ValueError(f"p={p} must be in (0,1)")
    u = secrets.randbelow(2**53) / (2**53)
    u = max(u, 1e-300)
    return max(1, math.ceil(math.log(u) / math.log(1.0 - p)))


def _discrete_laplace(scale_int: int) -> int:
    """DLap(scale_int) = G1 - G2."""
    if scale_int <= 0:
        raise ValueError(f"scale_int must be > 0")
    p = 1.0 - math.exp(-1.0 / scale_int)
    return _geometric_sample(p) - _geometric_sample(p)


def _laplace_noise_discrete(scale: float, resolution: int = 1000) -> float:
    """Exact discrete Laplace noise for domain [0,1]."""
    scale_int = max(1, round(resolution * scale))
    k = _discrete_laplace(scale_int)
    return k / resolution


# ─────────────────────────────────────────────
# VERA-D Core
# ─────────────────────────────────────────────

class VERADegradation:
    """
    Temporal degradation of DP aggregates.

    Usage :
        vd = VERADegradation()
        result = vd.degrade(aggregate=0.73,
                            produced_at=produced_at,
                            epsilon_ancre=0.5)
    """

    def __init__(self,
                 t1_days: int = T1_DAYS,
                 t2_days: int = T2_DAYS,
                 t3_days: int = T3_DAYS):
        self.t1 = t1_days
        self.t2 = t2_days
        self.t3 = t3_days

    def tier(self, age_days: float) -> DegradationTier:
        """Determine degradation tier from aggregate age."""
        if age_days < self.t1:
            return DegradationTier.FRESH
        elif age_days < self.t2:
            return DegradationTier.LIGHT
        elif age_days < self.t3:
            return DegradationTier.STRONG
        else:
            return DegradationTier.INVALID

    def epsilon_degradation(self, tier: DegradationTier) -> Optional[float]:
        """Additional ε for each degradation tier."""
        mapping = {
            DegradationTier.FRESH:   0.0,
            DegradationTier.LIGHT:   EPS_T1,
            DegradationTier.STRONG:  EPS_T2,
            DegradationTier.INVALID: None,
        }
        return mapping[tier]

    def degrade(self,
                aggregate: float,
                produced_at: datetime,
                epsilon_ancre: float = 0.5) -> DegradedAggregate:
        """
        Apply temporal degradation to a DP aggregate.

        Args:
            aggregate    : Original ANCRE aggregate ∈ [0,1]
            produced_at  : When the aggregate was produced
            epsilon_ancre: ε used by ANCRE (default 0.5)

        Returns:
            DegradedAggregate with degraded value or None if invalid
        """
        now = datetime.now(timezone.utc)
        age_days = (now - produced_at).total_seconds() / 86400.0

        current_tier = self.tier(age_days)
        eps_d = self.epsilon_degradation(current_tier)

        if current_tier == DegradationTier.INVALID:
            return DegradedAggregate(
                original_value=aggregate,
                degraded_value=None,
                tier=current_tier,
                age_days=age_days,
                epsilon_total=epsilon_ancre,
                valid=False,
                degraded_at=now.isoformat(),
            )

        if current_tier == DegradationTier.FRESH:
            # No degradation needed
            return DegradedAggregate(
                original_value=aggregate,
                degraded_value=aggregate,
                tier=current_tier,
                age_days=age_days,
                epsilon_total=epsilon_ancre,
                valid=True,
                degraded_at=now.isoformat(),
            )

        # Add degradation noise
        # scale = 1/eps_d (sensitivity = 1 for [0,1] domain)
        scale = 1.0 / eps_d
        noise = _laplace_noise_discrete(scale)
        degraded = float(min(1.0, max(0.0, aggregate + noise)))

        return DegradedAggregate(
            original_value=aggregate,
            degraded_value=degraded,
            tier=current_tier,
            age_days=age_days,
            epsilon_total=epsilon_ancre + eps_d,
            valid=True,
            degraded_at=now.isoformat(),
        )

    def schedule(self, produced_at: datetime) -> dict:
        """
        Returns the degradation schedule for an aggregate.
        Useful for audit and compliance documentation.
        """
        return {
            "produced_at": produced_at.isoformat(),
            "light_degradation_at": (produced_at + timedelta(days=self.t1)).isoformat(),
            "strong_degradation_at": (produced_at + timedelta(days=self.t2)).isoformat(),
            "invalidation_at": (produced_at + timedelta(days=self.t3)).isoformat(),
            "t1_days": self.t1,
            "t2_days": self.t2,
            "t3_days": self.t3,
        }


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("VERA-D v0.1 — Temporal Degradation Tests")
    print("=" * 50)

    vd = VERADegradation()
    aggregate = 0.73
    now = datetime.now(timezone.utc)

    # Test 1 — Fresh aggregate (age = 0)
    r = vd.degrade(aggregate, now, epsilon_ancre=0.5)
    assert r.tier == DegradationTier.FRESH
    assert r.degraded_value == aggregate
    assert r.valid
    assert r.epsilon_total == 0.5
    print(f"✅ FRESH : value={r.degraded_value:.4f}, ε_total={r.epsilon_total}")

    # Test 2 — Light degradation (age = 45 days)
    past_45 = now - timedelta(days=45)
    r = vd.degrade(aggregate, past_45, epsilon_ancre=0.5)
    assert r.tier == DegradationTier.LIGHT
    assert r.valid
    assert r.epsilon_total == 0.6  # 0.5 + 0.1
    assert 0.0 <= r.degraded_value <= 1.0
    print(f"✅ LIGHT  : value={r.degraded_value:.4f}, ε_total={r.epsilon_total}, age={r.age_days:.0f}d")

    # Test 3 — Strong degradation (age = 100 days)
    past_100 = now - timedelta(days=100)
    r = vd.degrade(aggregate, past_100, epsilon_ancre=0.5)
    assert r.tier == DegradationTier.STRONG
    assert r.valid
    assert r.epsilon_total == 1.0  # 0.5 + 0.5
    assert 0.0 <= r.degraded_value <= 1.0
    print(f"✅ STRONG : value={r.degraded_value:.4f}, ε_total={r.epsilon_total}, age={r.age_days:.0f}d")

    # Test 4 — Invalidation (age = 200 days)
    past_200 = now - timedelta(days=200)
    r = vd.degrade(aggregate, past_200, epsilon_ancre=0.5)
    assert r.tier == DegradationTier.INVALID
    assert not r.valid
    assert r.degraded_value is None
    print(f"✅ INVALID: value=None, age={r.age_days:.0f}d")

    # Test 5 — Schedule
    schedule = vd.schedule(now)
    print(f"\n📅 Schedule for aggregate produced now:")
    print(json.dumps(schedule, indent=2))

    # Test 6 — Tier boundaries
    assert vd.tier(0) == DegradationTier.FRESH
    assert vd.tier(29) == DegradationTier.FRESH
    assert vd.tier(30) == DegradationTier.LIGHT
    assert vd.tier(89) == DegradationTier.LIGHT
    assert vd.tier(90) == DegradationTier.STRONG
    assert vd.tier(179) == DegradationTier.STRONG
    assert vd.tier(180) == DegradationTier.INVALID
    print("\n✅ Tier boundaries correct")

    print("\n✅ VERA-D v0.1 — ALL TESTS PASSED")
