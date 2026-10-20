#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le lien de vote ne reste pas dans l'URL, sans casser la reprise (F13).

CONSTAT (audit externe du 19/10/2026, F13). Le credential de vote vit dans le
fragment (#a=...&d=...&k=...), qui ne part pas vers le serveur. Mais il restait
dans la barre d'adresse, l'onglet restaure et la synchronisation des onglets.

LE PIEGE. Retirer le fragment (history.replaceState) sans precaution casse la
reprise d'un vote signe mais non depose : au rechargement, le jeton n'est plus
lisible. Ce test verifie les deux choses a la fois.

CE QU'IL VERIFIE (fonction pure lireLien() de static/vote.html, EXECUTEE sous
node avec un faux sessionStorage)
  1. a l'arrivee, les parametres sont lus ET une copie est gardee ;
  2. au rechargement (URL sans fragment), le lien est relu depuis la copie ;
  3. sans fragment ni copie : aucun parametre (le message « lien incomplet ») ;
  4. un nouveau lien ecrase l'ancien ;
  5. stockage indisponible (qui leve) : pas de plantage, le fragment est lu ;
  6. la page retire bien le fragment (replaceState) et efface la copie au succes.

EXIGE node, comme test_cle_liee_au_groupe.
"""

import json
import pathlib
import re
import shutil
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


node = shutil.which("node")
if not node:
    print("IGNORE : node est absent.")
    raise SystemExit(2)

html = (RACINE / "static" / "vote.html").read_text(encoding="utf-8")
m = re.search(r"const CLE_LIEN_SESSION = .*?;\n  function lireLien\(.*?\n  \}\n", html, re.S)
verifier(m is not None, "0. lireLien() est retrouvee dans vote.html")

if m:
    script = m.group(0) + r"""
const faux = () => { const d = {}; return { d,
  getItem: k => (k in d ? d[k] : null), setItem: (k, v) => { d[k] = v; },
  removeItem: k => { delete d[k]; } }; };
const cassé = { getItem() { throw new Error('x'); }, setItem() { throw new Error('x'); } };
const sortie = {};
let s = faux();
let p = lireLien('#a=J1&d=Atelier&k=aa11', s);
sortie.arrivee = [p.get('a'), p.get('d'), p.get('k'), s.d[CLE_LIEN_SESSION]];
p = lireLien('', s);                       // rechargement : plus de fragment
sortie.rechargement = [p.get('a'), p.get('d'), p.get('k')];
p = lireLien('', faux());                  // ni fragment ni copie
sortie.vide = [p.get('a'), p.get('d')];
lireLien('#a=J2&d=Bureau&k=bb22', s);      // un nouveau lien ecrase l'ancien
p = lireLien('', s);
sortie.ecrase = [p.get('a'), p.get('d')];
p = lireLien('#a=J3&d=Direction&k=cc33', cassé);
sortie.casse_avec = [p.get('a'), p.get('d')];
p = lireLien('', cassé);
sortie.casse_sans = [p.get('a')];
p = lireLien('#a=J4&d=Atelier&k=dd44', null);
sortie.nul = [p.get('a')];
console.log(JSON.stringify(sortie));
"""
    r = subprocess.run([node, "-e", script], capture_output=True, text=True)
    verifier(r.returncode == 0, "1. la fonction s'execute sous node", r.stderr[:300])
    if r.returncode == 0:
        o = json.loads(r.stdout.strip().splitlines()[-1])
        verifier(o["arrivee"] == ["J1", "Atelier", "aa11", "a=J1&d=Atelier&k=aa11"],
                 "1a. a l'arrivee : parametres lus et copie gardee", str(o["arrivee"]))
        verifier(o["rechargement"] == ["J1", "Atelier", "aa11"],
                 "2. au rechargement (URL sans fragment) le lien est relu",
                 str(o["rechargement"]))
        verifier(o["vide"] == [None, None],
                 "3. sans fragment ni copie : aucun parametre", str(o["vide"]))
        verifier(o["ecrase"] == ["J2", "Bureau"],
                 "4. un nouveau lien ecrase l'ancien", str(o["ecrase"]))
        verifier(o["casse_avec"] == ["J3", "Direction"],
                 "5a. stockage qui leve : le fragment est quand meme lu",
                 str(o["casse_avec"]))
        verifier(o["casse_sans"] == [None] and o["nul"] == ["J4"],
                 "5b. stockage qui leve ou nul : pas de plantage", str(o))

verifier("history.replaceState(null, '', window.location.pathname + window.location.search)" in html,
         "6a. la page retire le fragment de l'URL (replaceState)")
verifier(re.search(r"function showSuccess\(\) \{\s*//[^\n]*\n\s*try \{ sessionStorage\.removeItem\(CLE_LIEN_SESSION\)", html) is not None,
         "6b. la copie du lien est effacee au succes")
verifier(html.index("history.replaceState") > html.index("const frag = lireLien("),
         "6c. le fragment est lu AVANT d'etre retire")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : le lien quitte l'URL sans casser la reprise d'un vote.")
sys.exit(0)
