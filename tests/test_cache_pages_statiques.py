#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les pages doivent etre REVALIDEES, et aucun `location` ne doit poser
d'en-tete qui ecraserait ceux du serveur.

CONSTAT (19/10/2026). Un deploiement avait ete verifie conforme -- le serveur
servait la bonne page d'administration -- mais le navigateur de l'organisateur
affichait encore l'ANCIENNE version, avec ses anciens en-tetes de securite.
Ni l'application ni nginx n'envoyaient de consigne de cache : le navigateur
reutilisait la page sans interroger le serveur. Pour une page de VOTE, ce serait
pire : le votant n'a aucun moyen de voir que sa page est perimee.

CE QUE CE TEST VERIFIE (infra/nginx-vera-consultation.conf, sans lancer nginx)
  1. `Cache-Control: no-cache` est pose au niveau `server` ;
  2. AUCUN `add_header` n'est pose dans un `location` (ni dans un bloc
     imbrique) : nginx n'herite des en-tetes du `server` que si le `location`
     n'en ajoute aucun. Un seul add_header de location ferait disparaitre, sur
     cette route, la CSP, HSTS, X-Frame-Options et le reste -- sans erreur,
     sans avertissement. Le fichier le dit en commentaire ; ce test l'impose.
  3. les cinq en-tetes de securite attendus sont toujours poses au niveau
     `server`, avec `always` (sinon ils disparaissent sur les reponses 4xx/5xx).
"""

import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
CONF = RACINE / "infra" / "nginx-vera-consultation.conf"

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


def directives_par_profondeur(texte):
    """Renvoie [(profondeur, ligne)] pour chaque directive `add_header`.

    Profondeur 0 = hors de tout bloc ; 1 = dans `server` (ou `http`) ; 2 et plus
    = dans un `location`, un `if`, etc. Les commentaires (# ...) sont retires
    AVANT de compter les accolades : une accolade dans un commentaire ou dans
    une chaine ne doit pas decaler le comptage.
    """
    profondeur = 0
    trouvees = []
    for brut in texte.splitlines():
        ligne = re.sub(r'"[^"]*"', '""', brut)      # chaines vides
        ligne = ligne.split("#", 1)[0]               # commentaires
        if re.match(r"\s*add_header\b", ligne):
            trouvees.append((profondeur, brut.strip()))
        profondeur += ligne.count("{") - ligne.count("}")
    return trouvees, profondeur


if not CONF.exists():
    print(f"ECHEC : {CONF} introuvable.")
    sys.exit(1)

texte = CONF.read_text(encoding="utf-8")
entetes, fin = directives_par_profondeur(texte)

verifier(fin == 0, "0. les accolades de la conf sont equilibrees",
         f"solde final = {fin}")

# Le bloc `server` est a la profondeur 1 : dans ce fichier, la conf ne contient
# pas de bloc `http {` englobant (c'est un fichier de site).
niveau_server = [l for p, l in entetes if p == 1]
dans_location = [l for p, l in entetes if p >= 2]

verifier(any(re.search(r'Cache-Control\s+"no-cache"\s+always;', l)
             for l in niveau_server),
         '1. « Cache-Control: no-cache » est pose au niveau server, avec always',
         "\n      ".join(niveau_server))

verifier(not dans_location,
         "2. aucun add_header dans un location (il ecraserait CSP, HSTS...)",
         "\n      ".join(dans_location))

for nom in ("Content-Security-Policy", "X-Frame-Options",
            "X-Content-Type-Options", "Referrer-Policy",
            "Strict-Transport-Security"):
    verifier(any(l.startswith(f'add_header {nom} ') and l.rstrip().endswith("always;")
                 for l in niveau_server),
             f"3. {nom} reste pose au niveau server, avec always")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : les pages sont revalidees et les en-tetes du server ne sont pas ecrases.")
sys.exit(0)
