#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_precision_kmin.py -- Verifie que la table de precision du README/AUDIT
est reproductible, ET que l'invariant structurel de la projection tient.

IMPORTANT sur la reproductibilite : OpenDP tire son bruit d'un CSPRNG interne
NON seedable (par conception, pour la securite). Ce test est donc STOCHASTIQUE :
il mesure une distribution, pas une valeur fixe. Les tolerances sont choisies
pour que le test soit stable a 3000 simulations tout en restant discriminant.
Ce n'est pas une preuve DP (voir validation_opendp.py) ; c'est un garde-fou
empirique : si la table de la doc s'ecarte de la mesure, le test echoue.

Principe (leçon du 14/07/2026) : une valeur annoncee dans la doc DOIT
correspondre a une mesure reproductible dans ses tolerances.
"""

import sys
import numpy as np
from vera_dp_noise import publier_histogramme_dp

# (effectif, erreur % attendue au 95e centile, tolerance)
TABLE_ATTENDUE = [
    (100, 12.0, 1.5),
    (150,  8.0, 1.5),
    (200,  6.0, 1.0),
    (240,  5.0, 0.8),
    (300,  4.0, 0.8),
    (500,  2.4, 0.6),
]

N_SIM = 3000

def _repartition_equilibree(n):
    """Repartition ~equilibree dont la somme fait EXACTEMENT n
    (la 3e case absorbe l'arrondi, sinon la baseline serait incoherente)."""
    a = round(n * 0.34)
    b = round(n * 0.33)
    c = n - a - b  # garantit a+b+c == n
    return {'oui': a, 'non': b, 'abstention': c}

def mesurer(n):
    vrai = _repartition_equilibree(n)
    assert sum(vrai.values()) == n, "baseline incoherente"
    errs = []
    for _ in range(N_SIM):
        pub = publier_histogramme_dp(vrai, n)
        # INVARIANT STRUCTUREL : la somme publiee DOIT valoir n exactement.
        assert sum(pub.values()) == n, f"projection cassee: somme={sum(pub.values())} != {n}"
        errs.append(max(abs(pub[k]-vrai[k]) for k in vrai))
    return 100 * np.percentile(np.array(errs), 95) / n

def main():
    print(f"Test de precision VERA (K_MIN=240, eps=0.5, {N_SIM} simulations)")
    print("Verifie aussi l'invariant somme(publie) == n a chaque tirage.")
    print(f"{'n':>5} {'attendu':>9} {'mesure':>9} {'verdict':>10}")
    print("-" * 38)
    ok = True
    for n, attendu, tol in TABLE_ATTENDUE:
        mesure = mesurer(n)
        passe = abs(mesure - attendu) <= tol
        ok = ok and passe
        print(f"{n:>5} {attendu:>8.1f}% {mesure:>8.1f}% {'PASS' if passe else 'FAIL':>10}")

    print("-" * 38)
    # A K_MIN=240, la promesse doit tenir. Tolerance stricte : 5.3% laisse une
    # marge de stabilite du 95e centile sans laisser passer une vraie derive.
    err_seuil = mesurer(240)
    promesse_ok = err_seuil <= 5.3
    print(f"Promesse a K_MIN=240 : erreur {err_seuil:.1f}% (doit rester <= 5.3%) ? {'OUI' if promesse_ok else 'NON'}")

    if ok and promesse_ok:
        print("\nTOUS LES TESTS PASSENT -- table reproductible + invariant somme=n verifie.")
        sys.exit(0)
    else:
        print("\nECHEC -- doc non reproduite ou invariant casse. A corriger.")
        sys.exit(1)

if __name__ == "__main__":
    main()
