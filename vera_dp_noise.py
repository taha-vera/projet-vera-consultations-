#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vera_dp_noise.py - Mecanisme de bruitage DP reel, branche sur les
endpoints qui publient des resultats agreges.

Recalibration 04/07/2026 (suite audit 3 IA independantes) :
- Ancien : Delta=10, scale=20, epsilon=0.5
- Nouveau : Delta=2, scale=4, epsilon=0.5 (meme garantie, bruit 5x plus faible)

Justification : la sensibilite reelle d'un vote binaire (oui/non/abstention)
est Delta=2 en modele de voisinage par substitution (bounded DP), pas Delta=10.
L'ancien Delta=10 etait une marge volontairement large non justifiee par la
structure des donnees, qui degradait inutilement la precision des resultats.

Canal temporel (Porte 3) : une fuite sub-microseconde est detectee
statistiquement par Mann-Whitney a N=10000 (p<0.001) sur les deux
configurations (scale=4 et scale=20). L'ecart de medianes est inferieur
a 1 microseconde dans les deux cas -- inexploitable via reseau HTTP dont
la latence est de l'ordre de 50-100 millisecondes. Formulation honnete :
fuite sub-microseconde detectee, non exploitable en conditions reelles.
"""

import opendp.prelude as dp

dp.enable_features("contrib")

DELTA_INT = 2
SCALE = 4.0
BOUNDS = (0, 100)

_domaine = dp.atom_domain(T=int, bounds=BOUNDS)
_metrique = dp.absolute_distance(T=int)
_mecanisme_laplace = dp.m.make_laplace(_domaine, _metrique, scale=SCALE)


def appliquer_bruit_dp(valeur_brute: int) -> int:
    valeur_bornee = max(BOUNDS[0], min(BOUNDS[1], valeur_brute))
    valeur_bruitee = _mecanisme_laplace(valeur_bornee)
    return max(0, valeur_bruitee)
