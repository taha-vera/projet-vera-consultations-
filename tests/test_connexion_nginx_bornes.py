#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Les routes de connexion sont bornees contre le client lent (F11).

CONSTAT (audit externe du 19/10/2026, F11). Le plafond de requetes simultanees
sur /api/rh/connexion (limit_conn, 8, cle constante) est PARTAGE : une seule
adresse qui ouvre huit connexions et envoie son corps goutte a goutte le remplit
et refuse la connexion a tous, l'organisateur compris -- donc la cloture, c'est-
a-dire l'effacement promis aux participants. Aucun delai ni taille de corps
n'etait fixe sur ces routes.

GARDE STRUCTURELLE (elle lit la conf, elle ne lance pas nginx). Pour chacune des
routes /api/rh/connexion et /api/admin/creer_compte_rh :
  1. le plafond global vera_login_conn est conserve ;
  2. un plafond PAR ADRESSE (vera_login_ip) s'y ajoute, et sa zone est declaree
     avec $binary_remote_addr ;
  3. client_body_timeout est court (<= 5 s) ;
  4. client_max_body_size est petit (<= 1 ko) -- la duree maximale d'une requete
     lente est approximativement (taille x delai) ;
  5. aucun plafond par adresse > 4 (sinon il ne protege plus le plafond global de 8).
Elle ne remplace pas un essai de charge : voir LIMITS.md.
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


def sans_commentaires(t):
    return "\n".join(l.split("#", 1)[0] for l in t.splitlines())


propre = sans_commentaires(texte)


def bloc(route):
    m = re.search(r"location\s*=\s*" + re.escape(route) + r"\s*\{", propre)
    if not m:
        return None
    i, prof = m.end(), 1
    j = i
    while j < len(propre) and prof:
        prof += {"{": 1, "}": -1}.get(propre[j], 0)
        j += 1
    return propre[i:j - 1]


def taille_octets(v):
    m = re.fullmatch(r"(\d+)([kKmM]?)", v)
    return int(m.group(1)) * {"": 1, "k": 1024, "m": 1024 ** 2}[m.group(2).lower()] if m else None


def secondes(v):
    m = re.fullmatch(r"(\d+)(ms|s|m)?", v)
    return int(m.group(1)) * {"ms": 0.001, None: 1, "s": 1, "m": 60}[m.group(2)] if m else None


zone = re.search(r"limit_conn_zone\s+(\S+)\s+zone=vera_login_ip:", propre)
verifier(zone is not None and zone.group(1) == "$binary_remote_addr",
         "0. la zone vera_login_ip est declaree avec $binary_remote_addr (par adresse)")

for route in ("/api/rh/connexion", "/api/admin/creer_compte_rh"):
    b = bloc(route)
    verifier(b is not None, f"{route} : bloc location retrouve")
    if b is None:
        continue
    verifier(re.search(r"limit_conn\s+vera_login_conn\s+\d+\s*;", b) is not None,
             f"{route} : le plafond global vera_login_conn est conserve")
    m = re.search(r"limit_conn\s+vera_login_ip\s+(\d+)\s*;", b)
    verifier(m is not None and int(m.group(1)) <= 4,
             f"{route} : plafond PAR ADRESSE present et <= 4",
             "absent" if not m else f"vaut {m.group(1)}")
    m = re.search(r"client_body_timeout\s+(\S+)\s*;", b)
    verifier(m is not None and secondes(m.group(1)) is not None and secondes(m.group(1)) <= 5,
             f"{route} : client_body_timeout court (<= 5 s)",
             "absent" if not m else f"vaut {m.group(1)}")
    m = re.search(r"client_max_body_size\s+(\S+)\s*;", b)
    verifier(m is not None and taille_octets(m.group(1)) is not None and taille_octets(m.group(1)) <= 1024,
             f"{route} : corps borne (<= 1 ko)",
             "absent" if not m else f"vaut {m.group(1)}")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : les routes de connexion sont bornees contre le client lent.")
sys.exit(0)
