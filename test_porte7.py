# =====================================================================
# Test Porte 7 : le "49/1" doit devenir impossible.
# 5 proprietes verifiees + simulation de l attaque complete.
# =====================================================================
from vera_token import Emetteur, Client, Agregateur, _fdh

em = Emetteur()
n, e = em.cle_publique()
ag = Agregateur(n, e)
ok = []

# --- 1. Flux nominal : emission -> contribution acceptee
c1 = Client(n, e)
sig = em.signer_aveugle("alice", "epoque-1", c1.aveugler())
token1 = c1.desaveugler(sig)
ag.contribuer("epoque-1", token1, 0.7)
ok.append(("1. flux nominal", True))

# --- 2. Double depense : le meme token resoumis doit etre REFUSE
try:
    ag.contribuer("epoque-1", token1, 0.9)
    ok.append(("2. double depense rejetee", False))
except PermissionError:
    ok.append(("2. double depense rejetee", True))

# --- 3. Deuxieme token meme individu meme epoque : REFUSE par l emetteur
c2 = Client(n, e)
try:
    em.signer_aveugle("alice", "epoque-1", c2.aveugler())
    ok.append(("3. un seul token/individu/epoque", False))
except PermissionError:
    ok.append(("3. un seul token/individu/epoque", True))

# --- 4. Epoque suivante : alice obtient un NOUVEAU token (partition, pas blocage)
c3 = Client(n, e)
sig3 = em.signer_aveugle("alice", "epoque-2", c3.aveugler())
ag.contribuer("epoque-2", c3.desaveugler(sig3), 0.4)
ok.append(("4. nouvelle epoque -> nouveau token", True))

# --- 5. Token forge sans signature valide : REFUSE
import secrets as _s
try:
    ag.contribuer("epoque-1", (_s.token_bytes(32), 12345), 0.5)
    ok.append(("5. token forge rejete", False))
except ValueError:
    ok.append(("5. token forge rejete", True))

# --- 6. Non-liaison (sanity) : ce que voit l emetteur (messages aveugles)
#     ne correspond a AUCUN serial depense chez l agregateur.
serials_vus = set()
for ep in ag.depenses.values():
    for srl in ep:
        serials_vus.add(_fdh(srl, n))
liaison = any(m in serials_vus for m in em.journal_aveugle)
ok.append(("6. non-liaison emetteur/agregateur", not liaison))

# --- 7. SIMULATION DE L ATTAQUE 49/1 (Dinur-Nissim)
#     50 individus contribuent a epoque-3. L organisateur malveillant veut
#     une 2e cohorte des 49 memes (sans "cible") DANS LA MEME EPOQUE.
em2 = Emetteur()
n2, e2 = em2.cle_publique()
ag2 = Agregateur(n2, e2)
for i in range(50):
    cl = Client(n2, e2)
    s = em2.signer_aveugle(f"ind-{i}", "epoque-3", cl.aveugler())
    ag2.contribuer("epoque-3", cl.desaveugler(s), 1.0 if i != 0 else 0.0)

refus = 0
for i in range(1, 50):  # les 49 sans la cible ind-0
    cl = Client(n2, e2)
    try:
        em2.signer_aveugle(f"ind-{i}", "epoque-3", cl.aveugler())
    except PermissionError:
        refus += 1
ok.append(("7. attaque 49/1 bloquee (49/49 refus)", refus == 49))
print(f"   cohorte 1 : {len(ag2.cohortes['epoque-3'])} contributions")
print(f"   cohorte 2 (differenciation) : {refus}/49 emissions REFUSEES")

# --- VERDICT
print()
tous = True
for nom, res in ok:
    print(f"{'OK  ' if res else 'FAIL'} {nom}")
    tous = tous and res
print()
print("PORTE 7 :", "FERMEE (prototype) - partition forcee, differenciation impossible"
      if tous else "ECHEC - revoir le module")
