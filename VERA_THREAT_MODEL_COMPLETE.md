# VERA / ANCRE — Modèle de menace : les 7 portes

*Auteur :* Taha Houari · tahahouari@hotmail.fr
*Date :* 2026-06-12
*Référence :* accompagne validation_opendp.py et README_VERA.md

## Principe

VERA protège un individu dont la contribution entre dans un agrégat publié.
Le modèle de menace est structuré en *7 portes* : 7 voies par lesquelles un
attaquant pourrait relier une réponse à une personne. Pour chaque porte :
la menace, la défense, et *l'état réel* (fermée / préliminaire /
hors-périmètre / ouverte). Aucun état n'est embelli.

## Porte 1 — Le mécanisme de bruit lui-même · *FERMÉE*

*Menace :* un bruit mal calibré ou mal échantillonné annule la garantie DP
(bug historique du projet : sampler maison, ratio pire cas 2,1 au lieu de 1,6487).
*Défense :* statistique snappée sur grille entière avant bruit
(Δ_int = 10), Laplace discret via OpenDP (bibliothèque auditée),
garantie ε = 0,5 calculée analytiquement par meas.map() — sans Monte Carlo.
*Preuve :* validation_opendp.py, reproductible.

## Porte 2 — Attaque par appartenance (MIA) · *PRÉLIMINAIRE*

*Menace :* déterminer si une personne donnée a participé à l'agrégat.
*Défense :* la garantie ε borne l'attaquant optimal (Neyman-Pearson).
AUC pire cas calculée analytiquement : 0,6209 ≤ borne théorique
0,6225 = e^ε/(1+e^ε). En conditions réalistes (contribution diluée),
AUC mesurée ≈ 0,505.
*État :* borne vérifiée analytiquement ; à consolider dans la suite de
tests versionnée.

## Porte 3 — Canal temporel · *PRÉLIMINAIRE*

*Menace :* le temps de calcul trahit la valeur d'entrée.
*Défense structurelle :* le tirage du bruit ne lit pas l'entrée ;
seul le snapping (arrondi) en dépend, en temps quasi constant.
*Mesure :* écart des médianes 2,83 % pour un bruit de mesure de 55 %
(Android/Termux) — aucune fuite détectable. Mesure fine à refaire en
environnement contrôlé.

## Porte 4 — Composition séquentielle · *PRÉLIMINAIRE*

*Menace :* répéter k requêtes sur les mêmes données épuise la protection.
ε_total = k·ε ; dès k=4 (ε=2,0), AUC max ≈ 0,88 : protection quasi nulle.
*Défense :* budget ε plafonné avec refus de servir au-delà (kill-switch),
et partition par token/époque (cf. Porte 7) forçant la composition parallèle
(ε reste 0,5 par époque).
*État :* arithmétique vérifiée ; le module de comptage versionné reste à
consolider (archives v03–v06 à unifier).

## Porte 5 — Observateur réseau (L1) · *HORS-PÉRIMÈTRE*

*Menace :* l'opérateur/infrastructure voit IP, horodatage, métadonnées.
*Position :* structurellement hors du contrôle de VERA — vrai pour tout
système applicatif. Mitigation externe possible (Tor, mixnets) non promise.
*Discipline :* ne jamais prétendre couvrir ce que l'architecture ne voit pas.

## Porte 6 — Coercition (L2) · *HORS-PÉRIMÈTRE*

*Menace :* contraindre un répondant à révéler ou prouver sa réponse.
*Position :* aucune solution technique côté agrégation ; un répondant
peut toujours se filmer en train de répondre. Limite partagée par tout
système (y compris vote papier par correspondance).

## Porte 7 — Différenciation par cohortes choisies, le « 49/1 » · *OUVERTE*

*Menace :* l'attaque fondatrice de la DP (Dinur-Nissim 2003) : un
organisateur malveillant interroge des cohortes qui se recouvrent
(50 personnes, puis 49 des mêmes) ; la différence des agrégats isole
l'individu manquant.
*Défense spécifiée :* un token anonyme à usage unique par individu et
par époque (k-TAA), imposant une structure de partition — chaque individu
ne contribue qu'à une cohorte par époque, ce qui force la composition
parallèle et rend la différenciation inopérante.
*État : NON IMPLÉMENTÉE.* La spécification existe, le code des tokens
n'existe pas. C'est le principal chantier ouvert du projet.

## Limites transverses (hors portes)

- *L3 — Petits effectifs :* sous un seuil N, l'anonymat est mathématiquement
  indélivrable quel que soit le bruit. Politique : refus de publier sous le seuil.
- *L4 — Qualification juridique :* anonymisation vs pseudonymisation au sens
  RGPD (art. 5(1)(e)) — relève d'un avis CNIL/DPO externe, non tranché ici.

## Synthèse

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | Fermée (preuve OpenDP) |
| 2. MIA | Préliminaire (borne analytique vérifiée) |
| 3. Canal temporel | Préliminaire (pas de fuite détectable) |
| 4. Composition | Préliminaire (budget spécifié) |
| 5. Observateur réseau | Hors-périmètre, assumé |
| 6. Coercition | Hors-périmètre, assumé |
| 7. Différenciation 49/1 | *Ouverte — à implémenter* |

Ce document dit ce qui est prouvé, ce qui est mesuré, ce qui est assumé
comme limite, et ce qui reste à faire. C'est sa fonction.
