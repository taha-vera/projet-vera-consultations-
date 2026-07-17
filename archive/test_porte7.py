# =====================================================================
# Test Porte 7 : le "49/1" doit devenir impossible.
# + liaison a l'epoque (un token ne vaut que pour SON epoque).
# =====================================================================
from vera_token import Emetteur, Client, Agregateur, _fdh

em = Emetteur()
n, e = em.cle_publique()
ag = Agregateur(n, e)
ok = []

# --- 1. Flux nominal : emission -> contribution acceptee
c1 = Client(n, e)
sig = em.signer_aveugle("alice", "epoque-1", c1.aveugler("epoque-1"))
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
    em.signer_aveugle("alice", "epoque-1", c2.aveugler("epoque-1"))
    ok.append(("3. un seul token/individu/epoque", False))
except PermissionError:
    ok.append(("3. un seul token/individu/epoque", True))

# --- 4. Epoque suivante : alice obtient un NOUVEAU token (partition, pas blocage)
c3 = Client(n, e)
sig3 = em.signer_aveugle("alice", "epoque-2", c3.aveugler("epoque-2"))
ag.contribuer("epoque-2", c3.desaveugler(sig3), 0.4)
ok.append(("4. nouvelle epoque -> nouveau token", True))

# --- 5. Token forge sans signature valide : REFUSE
import secrets as _s
try:
    ag.contribuer("epoque-1", (_s.token_bytes(32), 12345), 0.5)
    ok.append(("5. token forge rejete", False))
except ValueError:
    ok.append(("5. token forge rejete", True))
# --- 6. Non-liaison : l'emetteur (identites) et l'agregateur (serials)
#     n'ont AUCUNE valeur commune. L'emetteur ne stocke plus rien d'aveugle.
serials_vus = set()
for ep in ag.depenses.values():
    for srl in ep:
        serials_vus.add(srl)
liaison = any(srl in em.emis for srl in serials_vus)
ok.append(("6. non-liaison emetteur/agregateur", not liaison))

# --- 7. SIMULATION DE L ATTAQUE 49/1 (Dinur-Nissim)

em2 = Emetteur()
n2, e2 = em2.cle_publique()
ag2 = Agregateur(n2, e2)
for i in range(50):
    cl = Client(n2, e2)
    s = em2.signer_aveugle(f"ind-{i}", "epoque-3", cl.aveugler("epoque-3"))
    ag2.contribuer("epoque-3", cl.desaveugler(s), 1.0 if i != 0 else 0.0)

refus = 0
for i in range(1, 50):  # les 49 sans la cible ind-0
    cl = Client(n2, e2)
    try:
        em2.signer_aveugle(f"ind-{i}", "epoque-3", cl.aveugler("epoque-3"))
    except PermissionError:
        refus += 1
ok.append(("7. attaque 49/1 bloquee (49/49 refus)", refus == 49))
print(f"   cohorte 1 : {len(ag2.cohortes['epoque-3'])} contributions")
print(f"   cohorte 2 (differenciation) : {refus}/49 emissions REFUSEES")

# --- 8. LIAISON A L'EPOQUE : un token de epoque-1 doit etre REFUSE a epoque-2
#     C'est le correctif central : le FDH grave l'epoque dans la signature.
em3 = Emetteur()
n3, e3 = em3.cle_publique()
ag3 = Agregateur(n3, e3)
cli = Client(n3, e3)
# token fabrique POUR epoque-1
sig_e1 = em3.signer_aveugle("bob", "epoque-1", cli.aveugler("epoque-1"))
token_e1 = cli.desaveugler(sig_e1)
# tentative de rejeu du MEME token a epoque-2 -> doit etre REFUSE
try:
    ag3.contribuer("epoque-2", token_e1, 0.5)
    ok.append(("8. rejeu cross-epoque bloque", False))  # accepte = FAILLE
except ValueError:
    ok.append(("8. rejeu cross-epoque bloque", True))   # refuse = correct
# et il doit etre ACCEPTE a sa propre epoque-1
try:
    ag3.contribuer("epoque-1", token_e1, 0.5)
    ok.append(("8b. token valide a sa propre epoque", True))
except Exception:
    ok.append(("8b. token valide a sa propre epoque", False))

# --- VERDICT
print()
tous = True
for nom, res in ok:
    print(f"{'OK  ' if res else 'FAIL'} {nom}")
    tous = tous and res
print()
print("PORTE 7 :", "partition + liaison epoque VALIDEES (prototype)"
      if tous else "ECHEC - revoir le module")