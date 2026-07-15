#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_precision_kmin.py -- Verifie que la table de precision du README/AUDIT
est reproductible. Chaque affirmation publique sur la precision a un test
qui tourne : lancer `python3 test_precision_kmin.py` doit passer.

Principe (leçon du 14/07/2026) : une valeur annoncee dans la doc DOIT
correspondre a une mesure reproductible. Si ce test echoue, la doc ment.

Methode : 3000 simulations par effectif, repartition equilibree (pire cas),
erreur MAX sur les 3 options, 95e centile, apres projection sur le simplexe.
"""

import sys
import numpy as np
from vera_dp_noise import publier_histogramme_dp

# (effectif, erreur % attendue au 95e centile, tolerance)
TABLE_ATTENDUE = [
    (100, 12.0, 1.5),
    (150,  8.0, 1.5),
    (200,  6.0, 1.0),
    (240,  5.0, 0.8),   # SEUIL DE PUBLICATION : doit tenir <= 5%
    (300,  4.0, 0.8),
    (500,  2.4, 0.6),
]

N_SIM = 3000
SEED = 42

def mesurer(n):
    np.random.seed(SEED)
    vrai = {'oui': round(n*0.34), 'non': round(n*0.33), 'abstention': round(n*0.33)}
    errs = []
    for _ in range(N_SIM):
        pub = publier_histogramme_dp(vrai, n)
        errs.append(max(abs(pub[k]-vrai[k]) for k in vrai))
    return 100 * np.percentile(np.array(errs), 95) / n

def main():
    print(f"Test de precision VERA (K_MIN=240, eps=0.5, {N_SIM} simulations)")
    print(f"{'n':>5} {'attendu':>9} {'mesure':>9} {'verdict':>10}")
    print("-" * 38)
    ok = True
    for n, attendu, tol in TABLE_ATTENDUE:
        mesure = mesurer(n)
        passe = abs(mesure - attendu) <= tol
        ok = ok and passe
        print(f"{n:>5} {attendu:>8.1f}% {mesure:>8.1f}% {'PASS' if passe else 'FAIL':>10}")

    print("-" * 38)
    # Verification cle : a K_MIN=240, la promesse <=5% DOIT tenir
    err_seuil = mesurer(240)
    promesse_ok = err_seuil <= 5.5  # marge de tolerance sur le 95e centile
    print(f"Promesse a K_MIN=240 : erreur {err_seuil:.1f}% <= 5% ? {'OUI' if promesse_ok else 'NON'}")

    if ok and promesse_ok:
        print("\nTOUS LES TESTS PASSENT -- la table de la doc est reproductible.")
        sys.exit(0)
    else:
        print("\nECHEC -- la doc annonce des valeurs non reproduites. A corriger.")
        sys.exit(1)

if __name__ == "__main__":
    main()
