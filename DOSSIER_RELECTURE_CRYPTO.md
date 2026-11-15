# Dossier de relecture cryptographique

*À remettre à une personne qui relit la cryptographie de VERA. Rédigé le
24/10/2026 par le mainteneur (développeur seul, non cryptographe). Ce que ce
document affirme a été relevé dans le code ; ce qu'il ne sait pas, il le dit.*

## 1. Ce qu'on demande, et ce qu'on ne demande pas

VERA recueille des réponses anonymes (oui / non / abstention) dans une
organisation. Le serveur doit signer un justificatif **sans voir ce qu'il signe**,
puis compter la réponse **sans pouvoir la relier à l'invitation**. Un bruit de
Laplace (ε = 0,5) est ajouté aux totaux publiés.

**On demande** un avis sur : (a) l'usage de la signature aveugle RSA (§3 et
questions 1 à 5) ; (b) le bruit différentiel (question 8) ; (c) le chiffrement des
clés au repos (question 7).

**On ne demande pas** de relire l'interface, l'hébergement, ni la logique de
l'organisation. Les limites connues hors cryptographie (lien temporel entre deux
écritures en base, organisateur qui héberge lui-même, serveur qui servirait un
client modifié) sont écrites dans [LIMITS.md](LIMITS.md) ; inutile de les
redécouvrir.

## 2. Le protocole, de bout en bout

1. L'organisateur déclare ses groupes. Le serveur crée **une paire RSA par
   groupe** (2048 bits, e = 65537, durée de vie 7 jours) et calcule un
   **agrégat** : SHA-256 des couples (nom de groupe, clé publique) triés, chaque
   champ précédé de sa longueur sur 4 octets.
2. L'organisateur **publie cet agrégat hors du serveur** avant tout envoi. Chaque
   lien d'invitation porte, dans le fragment `#k=`, **l'agrégat** (l'empreinte de
   l'ensemble des clés), **et non la clé de son groupe** : le navigateur récupère
   les clés à part (`/api/cle_publique`, `/api/engagement_cles`). Correction du
   15/11/2026 : ce document disait l'inverse. Le lien étant fabriqué par le
   serveur, la comparaison automatique que fait le navigateur est circulaire ;
   seule la comparaison avec l'agrégat publié hors du serveur a une valeur, et la
   page n'offre aucun support pour la faire (elle n'affiche ni l'agrégat ni le
   groupe, et efface le fragment de la barre d'adresse).
3. Le navigateur du votant récupère toutes les clés, recalcule l'agrégat,
   le compare à celui du lien, refuse si le nombre de clés par groupe n'est pas
   un ou si la clé reçue pour son groupe n'est pas celle de l'ensemble.
4. Il tire `K` (32 octets, `crypto.getRandomValues`), fait
   `prepare(K)` → randomizer (32 octets) ‖ K, puis `blind`. Il envoie au serveur
   `jeton_autorisation` (à usage unique) et le message aveuglé.
5. Le serveur vérifie et consomme le jeton, signe aveuglément (RSA-PSS
   SHA-384, mode *Randomized*) et renvoie la signature aveugle.
6. Le navigateur finalise la signature, puis dépose `K`, `randomizer`,
   `signature`, la réponse et le groupe sur un **autre appel** (`/api/repondre`).
7. Le serveur vérifie la signature de `K` sous la clé du groupe, enregistre
   `SHA-384(K)` (anti-rejeu) et incrémente un compteur — dans une seule
   transaction. Aucune table ne contient à la fois un jeton et un `K`.

La réponse n'est **pas** couverte par la signature : seul `K` l'est.

## 3. Primitives et composants

| Élément | Valeur | Source |
|---|---|---|
| Schéma | RSABSSA-SHA384-PSS-Randomized, [RFC 9474](https://www.rfc-editor.org/rfc/rfc9474) | |
| Serveur | crate Rust `blind-rsa-signatures` 0.17.2, au-dessus de `rsa` **0.10.0-rc.18 (pré-version)**, pont `pyo3` 0.30.1 | `vera_blind_sig/` (139 lignes) |
| Client | `@cloudflare/blindrsa-ts` 0.4.4, empaqueté (esbuild), empreinte SRI sur la page | `chantier_crypto/`, `static/blindrsa-bundle.js` |
| Aléa serveur | `rand` (via `DefaultRng` du crate) ; `os.urandom` côté Python | à confirmer par vous (question 5) |
| Taille de clé | 2048 bits ; la signature fait 256 octets (contrôlé à la réception) | |
| Clés au repos | Fernet, clé dérivée de `VERA_DB_KEY` par PBKDF2-SHA256, 100 000 tours, sel de 16 octets par enregistrement | `vera_persistance.py:1448-1480` |
| Bruit | OpenDP `make_laplace`, domaine entier borné, `scale = 4,0`, sensibilité L1 = 2 | `vera_dp_noise.py` |

## 4. Ce qui a déjà été vérifié par machine (et seulement cela)

- **Vecteurs officiels de la RFC 9474** (annexe A.1, SHA-384 / PSS / Randomized) :
  `signer_aveugle`, `finaliser_signature` et `verifier_signature` rendent les
  octets de la RFC ; sept altérations sont refusées. Limites : le vecteur est en
  RSA 4096, pas 2048 ; `aveugler_message` n'est pas rejoué (il tire de
  l'aléa). `tests/test_vecteurs_rfc9474.py`.
- **Un jeton = une opération à clé privée, même en concurrence** (24 requêtes
  simultanées : une signature, un calcul) : `tests/test_signature_concurrente.py`,
  vérifié par mutant (sans le verrou, 24 calculs).
- **Epsilon annoncé, budget et échelle du bruit liés** :
  `tests/test_epsilon_lie_au_bruit.py`.
- **Interopérabilité client JS ↔ serveur Rust**, concurrence, et survie de
  l'anti-rejeu à un `kill -9` : `chantier_crypto/test_*.mjs`.
- **`cargo audit`** (24/10/2026) : 5 avis, 2 corrigés par mise à jour du verrou,
  3 restants et expliqués dans [LIMITS.md](LIMITS.md) §16. `npm audit` : voir
  même section.
- **Un vecteur qui passe ne prouve pas l'anonymat.** Il prouve que le calcul est
  celui de la RFC, rien de plus.

## 5. Les questions, par ordre d'importance

1. **Non-associabilité, au sens de la RFC.** Sous la clé d'un groupe, le serveur
   signe au plus autant de messages que le groupe a de personnes, en 7 jours. Les
   hypothèses de *blindness* de la RFC 9474 (voir ses considérations de sécurité)
   sont-elles tenues dans ce régime, avec
   `K` tiré par le client et le randomizer fourni par la bibliothèque ?
2. **Une clé par groupe, et l'agrégat.** Le serveur ne peut pas fournir une clé
   différente à chaque votant sans que l'agrégat publié ne le trahisse — **à
   condition** que quelqu'un le compare vraiment. La construction de l'agrégat
   (préfixes de longueur, tri par nom) est-elle sans ambiguïté ? Un groupe peut-il
   être découpé en sous-groupes qui ne changent pas l'agrégat ?
   Code : `agregat_cles` (`vera_signature_manager.py`), recalcul dans
   `static/vote.html` (autour de la ligne 800-860).
3. **La réponse n'est pas liée à la signature.** Quiconque possède `(K, signature)`
   peut déposer n'importe quelle réponse tant que `K` n'est pas consommé. Seul le
   votant connaît `K`. Y a-t-il un scénario réaliste où cela pose problème
   (par exemple un `K` observé en transit ou dans une sauvegarde d'écran) ?
4. **Anti-rejeu par `SHA-384(K)`.** Suffisant, ou faut-il lier explicitement
   `K` au groupe (aujourd'hui la clé du groupe fait ce travail) ?
5. **Pré-version `rsa` 0.10.0-rc.18 et aléa.** Le chemin de signature utilise
   `rsa_decrypt_and_check` avec aveuglement par un RNG, ce qui semble écarter
   l'attaque *Marvin* au niveau de la signature, mais l'avis RUSTSEC-2023-0071
   reste ouvert et sans correctif. Le risque est-il réel dans notre usage
   (signature uniquement, aucun déchiffrement exposé) ? Un fait qui borne
   l'exposition : chaque jeton ne déclenche qu'une opération à clé privée, un refus
   précède tout calcul et le rejeu renvoie la signature mémorisée ; le nombre
   d'opérations par clé est donc au plus l'effectif du groupe. **Ce fait était
   faux en concurrence jusqu'au 15/11/2026** : le contrôle du jeton et sa
   consommation étaient séparés par la signature, et 24 requêtes simultanées
   sur un même jeton exécutaient 24 opérations à clé privée (une seule signature
   livrée). Un verrou par jeton ferme ce cas ; `tests/test_signature_concurrente.py`
   le vérifie. Ce plafond suffit-il
   face aux attaques par canal temporel sur signature aveuglée ? Le RNG par défaut
   (`rand`) est-il un bon choix pour la génération de clés et l'aveuglement ?
6. **Taille de clé.** 2048 bits suffit-il pour une durée de vie de 7 jours et
   des signatures qui ne servent qu'à compter une fois ?
7. **Clés au repos.** Fernet + PBKDF2 à 100 000 tours, avec un secret d'exploitation
   (`VERA_DB_KEY`) que la documentation fait tirer au hasard sur 32 octets. La
   dérivation est-elle superflue ou dangereuse (secret déjà uniforme) ?
8. **Confidentialité différentielle.** ε = 0,5 par publication (sensibilité
   Δ₁ = 2, échelle du bruit 4,0), composition de base sur 4 publications par an et par population
   (LIMITS §14). Le mécanisme est entier (pas de flottants) ; l'arrondi final
   et la projection sur le simplexe sont du post-traitement. Le calcul de Δ₁ = 2
   (une personne change une réponse : deux cases bougent) est-il juste, et la
   publication de **trois** cases bruitées reste-t-elle à ε = 0,5 ?
   Cette partie relève peut-être d'une autre personne qu'un spécialiste de
   cryptographie à clé publique.

## 5bis. Écarts déjà relevés par des relectures internes (15/11/2026)

Une relecture indépendante par un autre modèle, confrontée au code, a produit ces
constats. Ils ne sont pas des questions à vous poser : ils sont donnés pour que vous
ne les redécouvriez pas, et pour que vous jugiez ce que nous en avons fait.

- **Signature et dépôt partent à quelques secondes d'écart** (le client enchaîne
  `/api/signer_aveugle` puis `/api/repondre`) ; la date d'ouverture les bloque tous
  deux à l'identique et ne les sépare donc pas. Un opérateur qui journalise les deux
  requêtes peut les rapprocher. C'est un risque **admis** (opérateur actif, hors
  garantie), désormais écrit dans LIMITS §9.
- **Un serveur malveillant peut fabriquer des liens à nom de groupe unique** : il
  isole chaque votant sans toucher au JavaScript, car le lien porte aussi l'agrégat
  que le client compare. Seule la comparaison hors bande y répond. Non corrigé.
- **La perte de la réponse de signature coûte la voix** : le client tire un nouveau
  `K` et un nouvel aveuglement à chaque envoi, donc le cache de rejeu du serveur ne
  sert jamais avec lui. Le texte qui promettait le contraire est corrigé ; le client
  reste à corriger.
- **Un groupe sous le seuil peut voter** : K_MIN ne protège que la publication ;
  l'effectif déclaré n'est contrôlé que par un avertissement.

## 6. Ce que nous savons ne pas savoir

- Personne n'a relu ce code avec les yeux d'un cryptographe. Tout ce qui précède
  est une lecture du mainteneur, plus des outils.
- Le client JavaScript est une bibliothèque tierce que nous empaquetons ; nous
  n'avons pas audité sa mise en œuvre de l'aveuglement (inversion, rejet des
  facteurs non inversibles).
- Un serveur qui servirait un JavaScript modifié casse l'anonymat sans toucher
  à la cryptographie. C'est documenté (§1 de
  [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)) et hors du
  champ de cette relecture.

## 7. Reproduire

```bash
git clone https://github.com/taha-vera/projet-vera-consultations-.git
cd projet-vera-consultations-
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt maturin
(cd vera_blind_sig && PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release --locked)
python3 tests/test_vecteurs_rfc9474.py     # vecteurs de la RFC
./run_tests.sh                             # suite complète
```

Fichiers à lire en priorité, dans cet ordre : `vera_blind_sig/src/lib.rs`,
`vera_signature_manager.py`, la route `/api/signer_aveugle` et la route
`/api/repondre` dans `vera_consultation_api.py`, `static/vote.html` (flux de
vote), `vera_dp_noise.py`.

Contact : le mainteneur, via les issues du dépôt.
