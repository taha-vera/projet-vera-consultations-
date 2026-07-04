# -*- coding: utf-8 -*-
"""
vera_dp_noise.py - Mecanisme de bruitage DP reel, branche sur les
endpoints qui publient des resultats agreges.

Parametres valides (Portes 1 et 3) : Delta_int=10, scale=20, bounds=(0,100)
-> epsilon = Delta_int/scale = 0.5 exact.
"""

import opendp.prelude as dp

dp.enable_features("contrib")

DELTA_INT = 10
SCALE = 20.0
BOUNDS = (0, 100)

_domaine = dp.atom_domain(T=int, bounds=BOUNDS)
_metrique = dp.absolute_distance(T=int)
_mecanisme_laplace = dp.m.make_laplace(_domaine, _metrique, scale=SCALE)


def appliquer_bruit_dp(valeur_brute: int) -> int:
    valeur_bornee = max(BOUNDS[0], min(BOUNDS[1], valeur_brute))
    valeur_bruitee = _mecanisme_laplace(valeur_bornee)
    return max(0, valeur_bruitee)
