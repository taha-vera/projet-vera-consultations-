#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""La reponse qui porte les jetons en clair ne touche jamais le disque de nginx.

CONSTAT (audit externe du 24/10/2026, N6). /api/rh/generer_autorisations
renvoie les jetons en clair ; elle passait par `location /`, aux valeurs par
defaut : nginx peut deverser une reponse volumineuse dans un fichier de
proxy_temp, puis l'effacer sans l'ecraser. La base ne garde que des empreintes
pour qu'un acces au disque ne permette pas de rejouer les jetons ; ce fichier
temporaire annulait cette precaution.

GARDE STRUCTURELLE (elle lit la conf, elle ne lance pas nginx). Pour la route :
  1. elle a un bloc `location =` dedie (pas le fourre-tout) ;
  2. ce bloc fixe `proxy_max_temp_file_size 0` ;
  3. il ne contient aucun add_header (il remplacerait les en-tetes de securite
     herites : CSP, HSTS) ;
  4. aucun `proxy_temp_path` n'est declare sur un chemin persistant sans raison :
     le reglage 2 suffit, un autre chemin ne le remplace pas.
Elle ne remplace pas un essai de charge avec un client lent : voir LIMITS.md.
"""

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
texte = (RACINE / "infra" / "nginx-vera-consultation.conf").read_text(encoding="utf-8")
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


propre = "\n".join(l.split("#", 1)[0] for l in texte.splitlines())
ROUTE = "/api/rh/generer_autorisations"

m = re.search(r"location\s*=\s*" + re.escape(ROUTE) + r"\s*\{", propre)
verifier(m is not None, f"1. {ROUTE} a un bloc location = dedie")
if m:
    i, prof, j = m.end(), 1, m.end()
    while j < len(propre) and prof:
        prof += {"{": 1, "}": -1}.get(propre[j], 0)
        j += 1
    b = propre[i:j - 1]
    t = re.search(r"proxy_max_temp_file_size\s+(\S+)\s*;", b)
    verifier(t is not None and t.group(1) == "0",
             "2. proxy_max_temp_file_size 0 : aucun deversement sur disque",
             f"trouve : {t.group(0) if t else 'rien'}")
    verifier("add_header" not in b,
             "3. aucun add_header (les en-tetes de securite herites sont conserves)")
    verifier("proxy_pass" in b and "limit_req" in b,
             "4. le bloc proxifie vers l'application et garde un plafond de debit")
    verifier("proxy_temp_path" not in b,
             "5. pas de proxy_temp_path : le reglage 0 est la protection, pas un autre dossier")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : les jetons en clair ne passent pas par un fichier temporaire de nginx.")
sys.exit(0)
