# VERA / ANCRE — Modèle de menace consolidé

**Auteur :** Taha Houari · tahahouari@hotmail.fr
**Version consolidée :** 2026-06-14
**Référence :** accompagne `validation_opendp.py`, `vera_token.py` et `README.md`

---

## Principe

VERA protège un individu dont la contribution entre dans un agrégat publié.
Le modèle de menace est structuré en **9 portes** : 9 voies par lesquelles un
attaquant pourrait relier une réponse à une personne. Pour chaque porte : la
menace, la défense, et **l'état réel** (fermée / préliminaire / mesurée /
hors-périmètre / module / gouvernance). Aucun état n'est embelli.

Deux invariants fondateurs sous-tendent l'ensemble :
1. **Non-persistance** : la donnée brute est détruite à l'entrée.
2. **Protection de ce qui reste** : les signaux et patterns conservés passent
   eux-mêmes par la protection DP, de sorte que rien de conservé ne désigne un
   individu. Détruire le brut est nécessaire mais non suffisant.

---

## Porte 1 — Mécanisme de bruit · **FERMÉE**

*Menace :* un bruit mal calibré ou mal échantillonné annule la garantie DP
(bug historique du projet : sampler maison, ratio pire cas 2,1 au lieu de 1,6487).

*Défense :* statistique snappée sur grille entière avant bruit (Δ_int = 10),
Laplace discret via OpenDP (bibliothèque auditée), garantie ε = 0,5 calculée
analytiquement par `meas.map()` — sans Monte Carlo.

*Preuve :* `validation_opendp.py`, reproductible.

---

## Porte 2 — Attaque par appartenance (MIA) · **PRÉLIMINAIRE**

*Menace :* déterminer si une personne donnée a participé à l'agrégat.

*Défense :* la garantie ε borne l'attaquant optimal (Neyman-Pearson). AUC pire
cas calculée analytiquement : 0,6209 ≤ borne théorique 0,6225 = e^ε/(1+e^ε).
En conditions réalistes (contribution diluée), AUC mesurée ≈ 0,505.

*Réserve :* l'AUC moyenne ne caractérise pas le pire cas par individu (cf.
Porte 8, métrique TPR @ bas FPR de Carlini). Borne vérifiée analytiquement ;
à consolider dans la suite de tests versionnée.

---

## Porte 3 — Canal temporel · **PRÉLIMINAIRE**

*Menace :* le temps de calcul trahit la valeur d'entrée.

*Défense structurelle :* le tirage du bruit ne lit pas l'entrée ; seul le
snapping (arrondi) en dépend, en temps quasi constant.

*Mesure :* écart des médianes 2,83 % pour un bruit de mesure de 55 %
(Android/Termux) — aucune fuite détectable. Mesure fine à refaire en
environnement contrôlé.

---

## Porte 4 — Composition séquentielle · **PRÉLIMINAIRE**

*Menace :* répéter k requêtes sur les mêmes données épuise la protection.
ε_total = k·ε ; dès k=4 (ε=2,0), AUC max ≈ 0,88 : protection quasi nulle.

*Défense :* budget ε plafonné avec refus de servir au-delà (kill-switch), et
partition par token/époque (cf. Porte 7) forçant la composition parallèle
(ε reste 0,5 par époque).

*État :* arithmétique vérifiée ; module de comptage versionné à consolider.

---

## Porte 5 — Observateur réseau (L1) · **MODULE OPTIONNEL**

*Menace :* l'opérateur/infrastructure (FAI type Orange, Bouygues, Free) voit
IP, horodatage, volume, métadonnées de connexion — en amont de VERA.

*Position :* le contenu et la destination sont chiffrés ; mais le fait même
de la connexion est visible et hors du contrôle applicatif de VERA. Aucun
système ne ferme cette porte — Tor, Nym, Signal l'atténuent sans la fermer.

*Traitement :* VERA prévoit un **module réseau optionnel** (VPN / Tor / mixnet)
que l'utilisateur active ou configure selon son modèle de menace. VERA
**oriente vers** ces briques existantes — il ne les réimplémente pas et ne
devient pas lui-même le point de confiance réseau. Choix laissé à l'utilisateur.

*Discipline :* ne jamais prétendre « l'opérateur ne voit rien » — promesse que
personne ne tient. VERA réduit ce que l'opérateur voit (contenu, destination),
pas le fait de la connexion.

---

## Porte 6 — Coercition (L2) · **HORS-PÉRIMÈTRE**

*Menace :* contraindre un répondant à révéler ou prouver sa réponse.

*Position :* aucune solution technique côté agrégation ; un répondant peut
toujours se filmer en train de répondre. Limite partagée par tout système, y
compris le vote papier par correspondance.

---

## Porte 7 — Différenciation par cohortes choisies, le « 49/1 » · **PARTITION VALIDÉE (prototype) ; CRYPTO À DURCIR**

*Menace :* l'attaque fondatrice de la DP (Dinur-Nissim 2003) : un organisateur
malveillant interroge des cohortes qui se recouvrent (50 personnes, puis 49 des
mêmes) ; la différence des agrégats isole l'individu manquant.

*Défense :* un token anonyme à usage unique par individu **et par époque**,
imposant une structure de partition — chaque individu ne contribue qu'à une
cohorte par époque, ce qui force la composition parallèle et rend la
différenciation inopérante.

*État de la mécanique — VALIDÉE :* `vera_token.py` + `test_porte7.py`, 9/9.
La liaison à l'époque est gravée dans le Full-Domain Hash (`FDH(serial‖epoque)`)
à l'aveuglage comme à la vérification : un token forgé pour l'époque T est
rejeté à toute autre époque (test 8) tout en restant valide à sa propre époque
(test 8b). L'attaque 49/1 simulée donne 49/49 émissions refusées (test 7).
Minimisation appliquée : l'émetteur ne conserve aucune trace du message aveugle
(`journal_aveugle` supprimé — réduit la surface de la Porte 9).

*État de la primitive cryptographique — NON SÉCURISÉE :* la signature aveugle
est un FDH/Chaum maison sans PSS, **forgeable par homomorphie**
(sig(a)·sig(b) = sig(a·b) mod n). Elle valide la LOGIQUE de partition, pas la
sécurité cryptographique.

*Durcissement (état de l'art vérifié 2026-06) :* la cible est RSABSSA / RFC 9474
(RSA-PSS). **Aucune bibliothèque Python conforme, packagée et maintenue n'existe
en 2026.** Les implémentations de référence actives sont en Rust
(github.com/jedisct1/rust-blind-rsa-signatures), TypeScript
(github.com/cloudflare/blindrsa-ts), Zig et Go. Le durcissement réel implique
donc soit une **migration multi-langage** du composant token, soit un **audit
crypto** — hors périmètre du prototype actuel. Coder RSABSSA à la main en Python
est explicitement écarté (discipline post-DLap : pas de primitive crypto maison
non auditée). Statut honnête : **mécanique validée, primitive à remplacer avant
toute production.**

---

## Porte 8 — Inférence directe sur l'outlier · **MESURÉE**

*Menace :* l'agrégat moyen (AUC ~0,62) masque la fuite sur le répondant
atypique — le « 1 non sur 99 ». Métrique correcte : TPR @ bas FPR (Carlini
2022), pas l'AUC moyenne. Attaque **distincte** de la Porte 7 : non plus la
différenciation structurelle, mais l'inférence directe sur la valeur de
l'outlier.

*Mesure — observation unique* (`test_porte8_outlier.py`, ε=0,5, Δ=10, scale=20) :
TPR@10 % = 16,3 % / TPR@1 % = 1,63 % / TPR@0,1 % = 0,16 %. À FPR 1 %,
l'attaquant n'attrape le vrai dissident que 1,6 % du temps (~1 % au hasard) :
**fuite négligeable sur une observation unique.** Baisser ε (0,1 ; 0,08)
n'améliore quasi rien : à ε=0,5 le bruit domine déjà le signal de l'outlier.

*Mesure — composition* (`test_porte8_composition.py`, attaquant qui moyenne k
observations du même outlier) : k=1 → 1,6 % ; k=10 → 9,7 % ; k=50 → 55,8 %
(anonymat effondré). La fuite croît en √k.

*Défense :* la partition de la Porte 7 — un token par individu par époque —
force **k=1 par époque**, ce qui maintient la fuite au niveau négligeable. Les
Portes 7 et 8 sont le **même rempart vu de deux côtés** : la partition
temporelle empêche l'accumulation qui ouvrirait la fuite outlier.

*Statut :* mesurée, négligeable à k=1 ; défense = partition Porte 7 ; limite
cross-époque assumée (cf. L5).

---

## Porte 9 — Collusion émetteur / agrégateur · **LIMITE DE GOUVERNANCE**

*Menace :* le token est co-généré par l'émetteur (qui connaît les identités)
et le client, puis vérifié par l'agrégateur (qui connaît les serials). Si
l'émetteur et l'agrégateur **colludent** — ou sont la même entité, ou l'un
compromet l'autre — le croisement de leurs registres peut casser l'anonymat.

*Défense :* aucune réponse purement cryptographique ; c'est une porte de
**gouvernance**. Elle se ferme par la **séparation organisationnelle** :
émetteur et agrégateur doivent être deux entités distinctes, sans intérêt à
colluder. La minimisation appliquée (Porte 7 : l'émetteur ne stocke aucun
message aveugle) réduit la surface mais ne supprime pas le risque structurel.

*Statut :* limite assumée, à traiter par l'architecture de déploiement, pas
par le code. À nommer explicitement dans tout contrat de déploiement.

---

## Limites transverses (hors portes)

**L3 — Petits effectifs :** sous un seuil N, l'anonymat est mathématiquement
indélivrable quel que soit le bruit. Politique : refus de publier sous le seuil.

**L4 — Qualification juridique :** anonymisation vs pseudonymisation au sens
RGPD (art. 5(1)(e), art. 17). Si l'agrégat reste ré-identifiable (cas outlier),
il est *pseudonyme* → art. 17 applicable. S'il est anonyme irréversible →
art. 17 sans objet. Le basculement dépend de la Porte 8. Relève d'un avis
CNIL/DPO externe — **non tranché ici** (saisine CNIL en cours).

**L5 — Accumulation cross-époque :** la partition (Porte 7) garantit k=1 *par
époque*, pas k=1 *à vie*. Un attaquant qui suit le même outlier répondant à la
même question sur k époques successives peut accumuler (cf. Porte 8
composition). Borné par le budget ε global (Porte 4) et coûteux en pratique.
Limite assumée.

---

## Synthèse

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | **Fermée** (preuve OpenDP) |
| 2. MIA | Préliminaire (borne analytique vérifiée) |
| 3. Canal temporel | Préliminaire (pas de fuite détectable) |
| 4. Composition séquentielle | Préliminaire (budget plafonné) |
| 5. Observateur réseau (L1) | Module optionnel (VPN/Tor, choix utilisateur) |
| 6. Coercition (L2) | Hors-périmètre, assumé |
| 7. Différenciation 49/1 | Partition validée (prototype) ; crypto à durcir |
| 8. Inférence outlier | Mesurée ; négligeable à k=1 ; défense = Porte 7 |
| 9. Collusion émetteur/agrégateur | Limite de gouvernance (séparation organisationnelle) |

| Limite transverse | Position |
|---|---|
| L3 — Petits effectifs | Refus de publier sous seuil |
| L4 — Qualification juridique | Avis CNIL/DPO requis, non tranché |
| L5 — Accumulation cross-époque | Assumée, bornée par budget ε global |

Ce document dit ce qui est prouvé, ce qui est mesuré, ce qui est assumé comme
limite, et ce qui reste à faire. C'est sa fonction.

---

## Annexe — Journal de bord (historique daté)

### 2026-06-12 — Porte 7 : spécification → prototype
Première implémentation de `vera_token.py` (tokens anonymes à usage unique par
signature aveugle RSA/Chaum, registre anti double-dépense). Validation initiale
`test_porte7.py` 7/7. La partition par époque est mécaniquement forcée →
composition parallèle → ε reste 0,5 par époque. Réserve posée : primitive
maison à remplacer par implémentation auditée (RSABSSA/RFC 9474) avant
production.

### 2026-06-14 — Porte 7 : correctif critique de liaison à l'époque
Faille identifiée par revue multi-IA : le FDH hashait le serial seul, sans lier
le token à son époque → un token restait valide à toute époque ultérieure (la
promesse « un par individu ET par époque » était fausse au niveau crypto).
Correctif : `FDH(serial‖epoque)` à l'aveuglage et à la vérification. Validation
9/9 dont test 8 (rejeu cross-époque bloqué) et 8b (token valide à sa propre
époque).

### 2026-06-14 — Porte 8 : mesure de la fuite outlier
Création de `test_porte8_outlier.py` (observation unique) et
`test_porte8_composition.py` (effet de k). Résultats : fuite négligeable à k=1
(1,6 % @ FPR 1 %), croissante en √k, effondrée à k=50 (55,8 %). Conclusion : la
partition de la Porte 7 est la défense de la Porte 8.

### 2026-06-14 — Porte 7 : minimisation + avertissement crypto
Suppression de `journal_aveugle` (l'émetteur ne conserve plus aucun message
aveugle — réduit la surface de la Porte 9). Avertissement explicite ajouté
au-dessus de `_fdh` : primitive forgeable, ne pas utiliser en production.
Test de non-liaison reformulé (séparation des registres émetteur/agrégateur).

