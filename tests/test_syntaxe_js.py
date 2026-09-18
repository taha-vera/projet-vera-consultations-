#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_syntaxe_js.py -- la syntaxe JS des pages statiques doit etre valide,
verifiee par un vrai interpreteur, pas seulement par un parseur HTML.

L'INCIDENT QUI JUSTIFIE CE TEST
Le 12/09/2026, un correctif sur static/vote.html a introduit des chaines de
caracteres JS adjacentes sans operateur de concatenation :

    showError(
      "premiere ligne "
      "deuxieme ligne",
      "titre"
    )

Valide en Python (concatenation implicite de litteraux adjacents). PAS valide
en JavaScript : c'est une erreur de syntaxe qui aurait rendu la fonction
entiere inexecutable au premier appel, en production, sur le chemin de vote.

Le validateur HTML utilise ailleurs dans ce depot (html.parser) ne l'a pas vu
-- il verifie que les BALISES sont bien formees, jamais le contenu d'un bloc
<script>. Aucun test existant sur ce depot n'invoque un vrai interprete JS.
Cette lacune a traverse plusieurs semaines et plusieurs dizaines de correctifs
sur ce meme fichier sans etre detectee -- seulement parce qu'aucun de ces
correctifs anterieurs n'avait produit d'erreur de syntaxe, pas parce qu'un
controle existait.

Ce test extrait le contenu de chaque <script> des pages statiques et le
soumet a `node --check` (analyse syntaxique seule, aucune execution). Si
`node` n'est pas installe, le test s'IGNORE proprement -- ce n'est pas un
defaut du projet, seulement une dependance de verification absente de cet
environnement precis.

Aucune dependance : ni base, ni module Rust, ni reseau (sauf node lui-meme,
deja present ou absent localement).
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = [
    os.path.join(RACINE, "static", "vote.html"),
    os.path.join(RACINE, "static", "admin.html"),
]


def main():
    node = shutil.which("node")
    if node is None:
        print("IGNORE : node n'est pas installe dans cet environnement.")
        print("  La syntaxe JS de static/*.html n'a pas ete verifiee ici.")
        return 0

    echecs = []
    for chemin in PAGES:
        nom = os.path.relpath(chemin, RACINE)
        if not os.path.isfile(chemin):
            echecs.append(f"{nom} : fichier introuvable.")
            continue

        contenu = open(chemin, encoding="utf-8").read()
        scripts = re.findall(r"<script>(.*?)</script>", contenu, re.S)
        if not scripts:
            continue  # pas de <script> inline, rien a verifier ici.

        for i, script in enumerate(scripts):
            with tempfile.NamedTemporaryFile(
                "w", suffix=".js", delete=False, encoding="utf-8"
            ) as f:
                f.write(script)
                chemin_tmp = f.name
            try:
                resultat = subprocess.run(
                    [node, "--check", chemin_tmp],
                    capture_output=True, text=True, timeout=10,
                )
                if resultat.returncode != 0:
                    detail = resultat.stderr.strip().splitlines()
                    detail = detail[0] if detail else "erreur inconnue"
                    echecs.append(
                        f"{nom}, bloc <script> n°{i + 1} : erreur de syntaxe "
                        f"JS -- {detail}"
                    )
            finally:
                os.unlink(chemin_tmp)

    if echecs:
        print("ECHEC : syntaxe JS invalide.\n")
        for e in echecs:
            print(f"  - {e}")
        return 1

    print("OK : la syntaxe JS de toutes les pages statiques est valide "
          "(verifiee par node --check).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
