#!/usr/bin/env python3
"""La page de vote, exercee dans un VRAI navigateur (Chromium) contre le vrai serveur.

Les autres gardes de static/vote.html lisent son source. Celui-ci le FAIT TOURNER :
un serveur local, un navigateur, un lien d'invitation reel, et des coupures reseau
provoquees au bon moment. Trouve le 15/11/2026 par une relecture independante, puis
reproduit ici avant d'etre corrige.

CE QUI ETAIT FAUX
  C. Si la reponse de signature se perdait (le serveur avait signe et consomme le
     jeton), le votant ne pouvait plus voter : le client tirait un nouveau secret et un
     nouvel aveuglement a chaque envoi, donc sa demande n'etait jamais identique et le
     serveur repondait « ce lien a deja servi ». Pareil si l'onglet se fermait entre la
     signature et le depot. LIMITS §1 et §12ter promettaient le contraire.
  D. Apres une cloture, le depot recevait 404 ; le client y voyait une panne reseau et
     invitait a reessayer sans fin (« Votre lien reste valable »).

CE QUE LE TEST VERIFIE
  1. reponse de signature perdue, meme onglet : un nouvel essai aboutit, UNE voix ;
  2. onglet ferme apres la perte, nouvel onglet : le vote aboutit, UNE voix de plus ;
  3. ce que le client conserve ne contient NI la reponse choisie NI autre chose que
     le materiel de signature, et tout est efface apres le depot ;
  4. un credentiel plus vieux que sa duree n'est pas rejoue (demande differente) ;
  5. la page affiche le groupe et l'alerte sous le seuil, sans injecter le nom du
     groupe comme du HTML ;
  6. apres une cloture, le votant lit « consultation terminee », pas « reessayez » ;
  7. la duree du credentiel est inferieure a la retention du serveur.

PREREQUIS : `pip install playwright` et `playwright install chromium`. Sans eux le test
est IGNORE (code 2), sauf si VERA_EXIGER_NAVIGATEUR=1 (la CI le pose : une garde qui
s'ignore en silence ne garde rien).
"""
import json
import os
import pathlib
import re
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
EXIGE = os.environ.get("VERA_EXIGER_NAVIGATEUR") == "1"


def ignorer(raison):
    if EXIGE:
        print(f"ECHEC : navigateur exige (VERA_EXIGER_NAVIGATEUR=1) mais indisponible : {raison}")
        raise SystemExit(1)
    print(f"IGNORE : {raison}")
    raise SystemExit(2)


if not os.environ.get("VERA_DB_PATH"):
    os.environ["VERA_DB_PATH"] = tempfile.mktemp(suffix=".db", prefix="vera_nav_")
os.environ.setdefault("VERA_DB_KEY", "0" * 64)
os.environ.setdefault("VERA_VERROU_PROCESSUS", os.environ["VERA_DB_PATH"] + ".lock")

try:
    import vera_blind_sig as vbs  # noqa: F401
    import uvicorn
except ImportError as e:
    ignorer(str(e))
try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    ignorer(f"playwright absent ({e})")

import vera_admin_auth as auth  # noqa: E402

MDP = "motdepasse_navigateur"
os.environ["VERA_ADMIN_USER"] = "rh_nav"
os.environ["VERA_ADMIN_HASH"] = auth.generer_empreinte(MDP)

import vera_consultation_api as api  # noqa: E402
import vera_persistance as persistance  # noqa: E402

if hasattr(api, "ECART_MINIMAL_OUVERTURE_SECONDES"):
    api.ECART_MINIMAL_OUVERTURE_SECONDES = 0

GROUPE = "Navigateur"
NB_LIENS = 8
echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


# ---- 7. duree du credentiel < retention du serveur (lecture du source) ----------
html = (RACINE / "static" / "vote.html").read_text(encoding="utf-8")
m = re.search(r"CREDENTIEL_DUREE_MS\s*=\s*(\d+)\s*\*\s*(\d+)\s*\*\s*(\d+)", html)
retention_ms = getattr(persistance, "RETENTION_SIGNATURES_SECONDS", 3600) * 1000
duree_ms = int(m.group(1)) * int(m.group(2)) * int(m.group(3)) if m else None
verifier(duree_ms is not None and 0 < duree_ms < retention_ms,
         "7. la duree du credentiel est inferieure a la retention des signatures du serveur",
         f"client : {duree_ms} ms ; serveur : {retention_ms} ms")

class Rep:
    """Reponse HTTP minimale (urllib : le venv de la CI n'a pas `requests`)."""
    def __init__(self, status, headers, corps):
        self.status_code, self.headers, self.text = status, headers, corps
        self.ok = 200 <= status < 300

    def json(self):
        return json.loads(self.text)


def requete(methode, url, donnees=None, entetes=None, delai=15):
    corps = None if donnees is None else json.dumps(donnees).encode("utf-8")
    en = {"Content-Type": "application/json", **(entetes or {})}
    rq = urllib.request.Request(url, data=corps, headers=en, method=methode)
    try:
        with urllib.request.urlopen(rq, timeout=delai) as r:
            return Rep(r.status, r.headers, r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return Rep(e.code, e.headers, e.read().decode("utf-8", "replace"))


# ---- serveur local ---------------------------------------------------------------
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    PORT = s.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"
serveur = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=PORT, log_level="error"))
threading.Thread(target=serveur.run, daemon=True).start()
for _ in range(150):
    try:
        if requete("GET", BASE + "/api/health", delai=1).ok:
            break
    except Exception:
        time.sleep(0.1)
else:
    ignorer("le serveur local ne repond pas")

r = requete("POST", BASE + "/api/rh/connexion", {"identifiant": "rh_nav", "mot_de_passe": MDP})
assert r.status_code == 200, r.text
cookie = re.search(r"session_vera=([^;]+)", r.headers["set-cookie"]).group(1)
ENTETES = {"Cookie": f"session_vera={cookie}"}


def rh(methode, chemin, json=None):
    return requete(methode, BASE + chemin, json, ENTETES)


assert rh("POST", "/api/rh/question", json={"intitule": "Question de test, navigateur ?"}).ok
assert rh("POST", "/api/rh/declarer_groupes", json={"groupes": [GROUPE], "effectifs": {GROUPE: 10}}).ok
assert rh("POST", "/api/rh/ouverture", json={"ouverture_unix": time.time() + 2}).ok
gen = rh("POST", "/api/rh/generer_autorisations", json={"departement": GROUPE, "quantite": NB_LIENS})
assert gen.ok, gen.text
liens = [a["lien_sms"] for a in gen.json()["autorisations"]]
time.sleep(2.5)


def url_de(lien):
    return BASE + "/vote" + lien[lien.index("#"):]


def votes():
    with api.verrou:
        return api.effectif_par_departement.get(GROUPE, 0)


def attendre(page, ident, ms=15000):
    try:
        page.locator("#" + ident).wait_for(state="visible", timeout=ms)
        return True
    except Exception:
        return False


def texte(page, ident):
    el = page.locator("#" + ident)
    return el.inner_text().strip() if el.count() and el.is_visible() else ""


def choisir(page):
    page.goto(url_de_courant[0])
    page.wait_for_selector("#options-container input", timeout=15000)
    premier = page.locator("#options-container input").first
    premier.check()
    return premier.get_attribute("value")


def perdre_premiere_reponse(page):
    """La premiere reponse de /api/signer_aveugle est PERDUE : le serveur signe et
    consomme le jeton, mais le navigateur ne la recoit jamais."""
    etat = {"n": 0}

    def gestionnaire(route):
        if etat["n"] == 0:
            etat["n"] += 1
            route.fetch()
            route.abort()
        else:
            route.continue_()
    page.route("**/api/signer_aveugle", gestionnaire)


def cles_cred(page):
    return page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('vera_cred:'))")


def cles_pending(page):
    return page.evaluate("Object.keys(sessionStorage).filter(k => k.startsWith('vera_pending:'))")


url_de_courant = [None]

try:
    with sync_playwright() as p:
        try:
            navigateur = p.chromium.launch()
        except Exception as e:
            ignorer(f"chromium indisponible ({str(e).splitlines()[0][:90]})")

        # ---- 5. groupe affiche, alerte sous le seuil, pas d'injection HTML --------
        print("5. Groupe affiche et alerte sous le seuil")
        ctx = navigateur.new_context()
        page = ctx.new_page()
        page.goto(url_de(liens[7]))
        page.wait_for_selector("#options-container input", timeout=15000)
        page.wait_for_timeout(1500)
        info = texte(page, "info-groupe")
        verifier(f"« {GROUPE} »" in info, "le groupe du lien est affiche", repr(info))
        verifier(f"{NB_LIENS} invitation(s)" in info and "240" in info,
                 "l'alerte annonce l'effectif declare et le seuil", repr(info))
        verifier("identifiable" not in info.lower(),
                 "le texte n'accole pas « reponse » et « identifiable » (regle de la page)")
        ctx.close()
        ctx = navigateur.new_context()
        page = ctx.new_page()
        faux = url_de(liens[7]).replace(f"d={GROUPE}", "d=%3Cb%20id%3D%22inj%22%3Ex%3C%2Fb%3E")
        page.goto(faux)
        page.wait_for_timeout(2500)
        verifier(page.locator("#inj").count() == 0,
                 "un nom de groupe contenant du HTML n'est pas injecte dans la page")
        ctx.close()

        # ---- 1 + 3. reponse perdue, meme onglet -----------------------------------
        print("1. Reponse de signature perdue, meme onglet")
        ctx = navigateur.new_context()
        page = ctx.new_page()
        url_de_courant[0] = url_de(liens[0])
        reponse = choisir(page)
        perdre_premiere_reponse(page)
        avant = votes()
        page.locator("#submit-btn").click()
        page.wait_for_timeout(2500)
        cles = cles_cred(page)
        verifier(len(cles) == 1, "un credentiel est conserve AVANT l'envoi", f"{cles}")
        if cles:
            brut = page.evaluate("k => localStorage.getItem(k)", cles[0])
            champs = set(json.loads(brut).keys())
            verifier(champs == {"t", "pub", "prepared", "inv", "blinded"},
                     "3. le credentiel ne contient que du materiel de signature",
                     f"champs : {sorted(champs)}")
            verifier(reponse not in brut,
                     "3. la reponse choisie n'est JAMAIS ecrite dans localStorage",
                     f"« {reponse} » retrouve dans {brut[:80]}")
        page.locator("#submit-btn").click()
        verifier(attendre(page, "success-screen"),
                 "le nouvel essai aboutit (ecran de confirmation)",
                 f"ecran d'erreur : {texte(page, 'error-screen')[:120]!r}")
        verifier(votes() == avant + 1, "exactement UNE voix est comptee",
                 f"{avant} -> {votes()}")
        verifier(cles_cred(page) == [] and cles_pending(page) == [],
                 "3. tout est efface apres le depot")
        ctx.close()

        # ---- 2. onglet ferme apres la perte ---------------------------------------
        print("2. Onglet ferme apres la perte de la reponse")
        ctx = navigateur.new_context()
        page = ctx.new_page()
        url_de_courant[0] = url_de(liens[1])
        choisir(page)
        perdre_premiere_reponse(page)
        avant = votes()
        page.locator("#submit-btn").click()
        page.wait_for_timeout(2500)
        page.close()
        page2 = ctx.new_page()
        choisir(page2)
        page2.locator("#submit-btn").click()
        verifier(attendre(page2, "success-screen"),
                 "un NOUVEL onglet aboutit grace au credentiel conserve",
                 f"ecran d'erreur : {texte(page2, 'error-screen')[:120]!r}")
        verifier(votes() == avant + 1, "exactement UNE voix de plus", f"{avant} -> {votes()}")
        ctx.close()

        # ---- 4. credentiel perime : pas rejoue ------------------------------------
        print("4. Credentiel perime")
        ctx = navigateur.new_context()
        page = ctx.new_page()
        url_de_courant[0] = url_de(liens[2])
        choisir(page)
        corps = []
        page.on("request", lambda rq: corps.append(rq.post_data)
                if rq.url.endswith("/api/signer_aveugle") else None)
        perdre_premiere_reponse(page)
        page.locator("#submit-btn").click()
        page.wait_for_timeout(2500)
        page.evaluate("""() => { for (const k of Object.keys(localStorage)) {
            if (!k.startsWith('vera_cred:')) continue;
            const c = JSON.parse(localStorage.getItem(k)); c.t = Date.now() - 56 * 60 * 1000;
            localStorage.setItem(k, JSON.stringify(c)); } }""")
        page.locator("#submit-btn").click()
        page.wait_for_timeout(2500)
        verifier(len(corps) == 2 and corps[0] != corps[1],
                 "un credentiel de 56 min n'est pas rejoue (demande differente)",
                 f"{len(corps)} demande(s)")
        ctx.close()

        # ---- 6. apres cloture ------------------------------------------------------
        print("6. Cloture entre la signature et le depot")
        ctx = navigateur.new_context()
        page = ctx.new_page()
        url_de_courant[0] = url_de(liens[3])
        choisir(page)
        coupes = {"n": 0}

        def couper_depot(route):
            if coupes["n"] == 0:
                coupes["n"] += 1
                route.abort()
            else:
                route.continue_()
        page.route("**/api/repondre", couper_depot)
        page.locator("#submit-btn").click()
        page.wait_for_timeout(3000)
        verifier("Réessayer" in page.locator("#submit-btn").inner_text(),
                 "le depot coupe propose de reessayer (cas normal)")
        verifier(rh("POST", "/api/rh/cloturer").status_code == 200, "cloture par l'organisateur")
        page.locator("#submit-btn").click()
        verifier(attendre(page, "error-screen"), "un ecran d'erreur final s'affiche")
        t = texte(page, "error-screen")
        verifier("terminée" in t and "PAS été enregistrée" in t,
                 "il dit que la consultation est terminee et la voix non enregistree", repr(t[:160]))
        verifier("reste valable" not in t, "il ne promet pas un lien encore valable", repr(t[:160]))
        verifier(cles_cred(page) == [] and cles_pending(page) == [],
                 "tout est efface")
        ctx.close()
        navigateur.close()
finally:
    serveur.should_exit = True

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for e in echecs:
        print("  - " + e)
    sys.exit(1)
print("OK : la page de vote, dans un vrai navigateur, rattrape une signature perdue et dit vrai apres une cloture.")
sys.exit(0)
