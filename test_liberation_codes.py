#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_liberation_codes.py -- Point 3 audit Fable 5. Verifie que la logique de
suppression d'un code court apres consommation du token fonctionne : un code
consomme est retire du registre (evite la saturation cumulative).

Test cible sur les fonctions de persistance + la logique de recherche/suppression,
sans monter tout le serveur FastAPI. Base jetable, prod jamais touchee.
"""
import os, sys, tempfile
from pathlib import Path

os.environ["VERA_DB_KEY"] = "cle_test_liberation"
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
    print("Test liberation des codes courts apres vote (base jetable)")
    print("-" * 56)
    ok = True

    # Simule le registre memoire {code: token} et la persistance.
    registre = {}

    # 1. Generer 3 codes (comme a la generation de tokens).
    try:
        for code, tok in [("1111", "tokenA"), ("2222", "tokenB"), ("3333", "tokenC")]:
            registre[code] = tok
            p.persister_code_court(code, tok)
        if len(registre) != 3 or len(p.charger_codes_courts()) != 3:
            raise Echec("les 3 codes devraient etre presents (memoire + base)")
        _ok("1. trois codes generes (memoire + base)")
    except Echec as e:
        print(f"FAIL 1. {e}"); ok = False

    # 2. Simuler un vote avec tokenB : retrouver le code par le token, le supprimer.
    #    (C'est exactement la logique ajoutee dans /api/repondre.)
    try:
        token_vote = "tokenB"
        code_a_liberer = None
        for _code, _tok in registre.items():
            if _tok == token_vote:
                code_a_liberer = _code
                break
        if code_a_liberer != "2222":
            raise Echec(f"mauvais code retrouve: {code_a_liberer} (attendu 2222)")
        registre.pop(code_a_liberer, None)
        p.supprimer_code_court(code_a_liberer)
        _ok("2. vote avec tokenB -> code 2222 identifie et supprime")
    except Echec as e:
        print(f"FAIL 2. {e}"); ok = False

    # 3. Verifier que le code est bien parti (memoire ET base), les autres restent.
    try:
        if "2222" in registre:
            raise Echec("le code 2222 devrait etre absent de la memoire")
        codes_base = p.charger_codes_courts()
        if "2222" in codes_base:
            raise Echec("le code 2222 devrait etre absent de la base")
        if "1111" not in codes_base or "3333" not in codes_base:
            raise Echec("les autres codes (1111, 3333) devraient rester")
        _ok("3. code libere (memoire+base), les autres intacts")
    except Echec as e:
        print(f"FAIL 3. {e}"); ok = False

    # 4. L'espace s'est bien reduit : 3 -> 2 codes actifs.
    try:
        if len(registre) != 2 or len(p.charger_codes_courts()) != 2:
            raise Echec(f"il devrait rester 2 codes actifs (memoire={len(registre)}, base={len(p.charger_codes_courts())})")
        _ok("4. espace reduit 3 -> 2 (saturation cumulative evitee)")
    except Echec as e:
        print(f"FAIL 4. {e}"); ok = False

    _nettoyer()
    print("-" * 56)
    if ok:
        print("Point 3 OK : voter libere le code, l'espace ne sature plus cumulativement.")
        sys.exit(0)
    else:
        print("ECHEC.")
        sys.exit(1)

if __name__ == "__main__":
    main()
