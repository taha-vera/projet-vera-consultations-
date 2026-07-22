import os
import vera_persistance as p

p.initialiser()

# 1. Poser des jetons d'autorisation (registre 1)
p.persister_jeton_autorisation("jeton_A", "dept_1")
p.persister_jeton_autorisation("jeton_B", "dept_1")
avant = p.charger_jetons_autorisation()
print("1. jetons poses:", len(avant), "(attendu 2)")

# 2. Cloturer -> effacer_etat_consultation
p.effacer_etat_consultation()

# 3. Verifier que la table jetons_autorisation est VIDE
apres = p.charger_jetons_autorisation()
print("2. jetons apres cloture:", len(apres), "(attendu 0)")

ok = (len(avant) == 2 and len(apres) == 0)
print("TEST EFFACEMENT JETONS: OK" if ok else "TEST ECHOUE")
import sys
sys.exit(0 if ok else 1)
