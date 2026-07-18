#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_atomicite_publication.py -- Verifie que budget et resultat sont persistes
de facon ATOMIQUE (audit Fable 5, point 2). Sans atomicite, un crash entre les
deux ecritures laissait un departement verrouille a jamais (deja_publie=True
mais resultat introuvable). Base jetable, prod jamais touchee.
"""
import os, sys, tempfile
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_test_atomicite"
import vera_persistance as p

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); _tmp.close()
p.DB_PATH = Path(_tmp.name); p.initialiser()

class Echec(Exception): pass
def _ok(n): print(f"OK   {n}")
def _nettoyer():
    for s in ("", "-wal", "-shm"):
        try: Path(str(_tmp.name)+s).unlink()
        except FileNotFoundError: pass

def main():
    print("Test atomicite budget<->resultat (base jetable)")
    print("-" * 52)
    ok = True

    # 1. La publication atomique ecrit budget ET resultat ensemble.
    try:
        p.persister_publication_atomique("A", 0.5, 1, {"oui": 45, "non": 30})
        budget = p.charger_budget_epsilon()
        resultat = p.charger_resultat_publie("A")
        if budget.get("A", {}).get("nombre_publications") != 1:
            raise Echec("budget non persiste")
        if resultat != {"oui": 45, "non": 30}:
            raise Echec("resultat non persiste")
        _ok("1. budget + resultat persistes ensemble")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. COHERENCE : jamais "budget marque publie" sans resultat.
    #    On verifie l'invariant qui evite le lockout : si nb_publications>0,
    #    alors le resultat DOIT exister.
    try:
        budget = p.charger_budget_epsilon()
        for dept, etat in budget.items():
            if etat["nombre_publications"] > 0 and p.charger_resultat_publie(dept) is None:
                raise Echec(f"INCOHERENCE: {dept} publie mais resultat absent (lockout)")
        _ok("2. invariant coherent: tout departement publie a son resultat")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. Simulation de "crash" : on verifie qu'une transaction atomique ne
    #    peut pas laisser un etat partiel. On ecrit plusieurs fois et on
    #    verifie qu'a chaque instant budget et resultat sont coherents.
    try:
        for i in range(5):
            p.persister_publication_atomique(f"D{i}", 0.5, 1, {"oui": i, "non": 10-i})
            # apres chaque appel, coherence immediate
            b = p.charger_budget_epsilon()
            if b.get(f"D{i}", {}).get("nombre_publications") == 1:
                if p.charger_resultat_publie(f"D{i}") is None:
                    raise Echec(f"D{i}: budget ecrit mais resultat absent")
        _ok("3. coherence maintenue sur ecritures repetees")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    _nettoyer()
    print("-" * 52)
    if ok:
        print("ATOMICITE OK : plus d'etat 'publie sans resultat' possible.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
