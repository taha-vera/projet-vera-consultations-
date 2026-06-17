import math
import secrets
import opendp.prelude as dp
from vera_token import Emetteur, Client, Agregateur
dp.enable_features("contrib")

EPS_CIBLE = 0.5
K_MIN = 100
EPSILON_MAX = 1.5
R = 1000  # resolution de grille pour une moyenne sur [0,1]

print(f"[VERA] Mecanisme : Laplace OpenDP, epsilon cible = {EPS_CIBLE}")

def publier(agg, epoque, budget):
    reponses = agg.cohortes.get(epoque, [])
    n = len(reponses)
    if n < K_MIN:
        return f"REFUS : {n} < K_MIN={K_MIN}", budget
    if budget + EPS_CIBLE > EPSILON_MAX + 1e-9:
        return f"KILL-SWITCH : budget {budget}/{EPSILON_MAX} epuise", budget
    # Moyenne sur [0,1]. Sensibilite d une moyenne = 1/n.
    # Sur grille entiere (x R) : sensibilite entiere = ceil(R/n).
    vrai = sum(reponses) / n
    delta_int = math.ceil(R / n)
    scale = delta_int / EPS_CIBLE
    space = dp.atom_domain(T=int), dp.absolute_distance(T=int)
    meas = space >> dp.m.then_laplace(scale=scale)
    eps_reel = meas.map(d_in=delta_int)
    publie_int = meas(round(vrai * R))
    publie = max(0.0, min(1.0, publie_int / R))
    budget += EPS_CIBLE
    agg.cohortes[epoque] = []
    return f"OK : n={n} | vrai={vrai:.3f} | publie={publie:.3f} | eps={eps_reel:.2f} | budget={budget}/{EPSILON_MAX}", budget

print("\n=== CONSULTATION : cfdt-2026 ===")
emetteur = Emetteur()
n, e = emetteur.cle_publique()
agg = Agregateur(n, e)
EPOQUE = "cfdt-2026"
budget = 0.0
nb = 200
for i in range(nb):
    cli = Client(n, e)
    sig = emetteur.signer_aveugle(f"personne_{i}", EPOQUE, cli.aveugler(EPOQUE))
    agg.contribuer(EPOQUE, cli.desaveugler(sig), 1 if secrets.randbelow(100) < 52 else 0)
print(f"  {nb} participants ont repondu (1 token chacun)")

try:
    cli2 = Client(n, e)
    emetteur.signer_aveugle("personne_0", EPOQUE, cli2.aveugler(EPOQUE))
    print("  [!] ANOMALIE : double emission acceptee")
except PermissionError:
    print("  Double-emission personne_0 : REFUSEE")

print("\n  -- Publications --")
for essai in range(1, 5):
    agg.cohortes[EPOQUE] = [1 if secrets.randbelow(100) < 52 else 0 for _ in range(nb)]
    msg, budget = publier(agg, EPOQUE, budget)
    print(f"  Publication {essai}: {msg}")

print("\n=== FIN : resultat bruite publie, brut detruit ===")
