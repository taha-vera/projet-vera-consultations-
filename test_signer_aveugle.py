#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test logique endpoint /api/signer_aveugle (brique 2 refactor crypto)."""
import tempfile, sys
from pathlib import Path
import vera_persistance as p
import vera_blind_sig as vbs

def main():
    t = tempfile.NamedTemporaryFile(suffix=".db", delete=False); t.close()
    p.DB_PATH = Path(t.name); p.initialiser()
    sk, pk = vbs.generer_cles()
    p.persister_jeton_autorisation("j1", "dept_test")
    msg = b'{"vote":"oui"}'
    bm, sec, rnd = vbs.aveugler_message(list(pk), list(msg))
    dept = p.consommer_jeton_autorisation("j1")
    sig_av = bytes(vbs.signer_aveugle(list(sk), list(bm)))
    rejeu = p.consommer_jeton_autorisation("j1")
    sig = bytes(vbs.finaliser_signature(list(pk), list(msg), list(bm), list(sec), list(sig_av), list(rnd)))
    valide = vbs.verifier_signature(list(pk), list(msg), list(sig), list(rnd))
    ok = (dept == "dept_test" and len(sig_av) == 256 and rejeu is None and valide)
    print("jeton->dept:", dept, "| sig_av:", len(sig_av), "| rejeu:", rejeu, "| valide:", valide)
    print("OK" if ok else "ECHEC")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
