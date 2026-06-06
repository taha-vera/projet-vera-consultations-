# Section 1 — Contexte et Problème

## 1.1 Le Problème des Données d'Écoute Radio

Les plateformes de diffusion audio collectent en temps réel des données d'écoute granulaires : quel utilisateur écoute quelle émission, à quelle heure, depuis quel appareil, pendant combien de temps. Ces données ont une valeur commerciale considérable pour les opérateurs d'intelligence artificielle qui souhaitent entraîner des modèles de recommandation, d'analyse de tendances ou de ciblage publicitaire.

Cependant, ces données sont également **sensibles au sens du RGPD** (Règlement Général sur la Protection des Données, UE 2016/679). Les habitudes d'écoute révèlent des préférences politiques, religieuses ou culturelles protégées. Une plateforme radio qui vend ces données brutes s'expose à des sanctions substantielles (jusqu'à 4% du chiffre d'affaires mondial, Article 83 RGPD) et à une perte de confiance de ses auditeurs.

La tension est donc la suivante :

```
Données brutes    → Valeur commerciale maximale, non vendables (RGPD)
Données agrégées  → Légalement vendables, valeur commerciale réduite
```

**Question centrale** : Existe-t-il un mécanisme permettant de produire des agrégats statistiquement utiles, avec une garantie mathématique de protection individuelle, vendables légalement à des opérateurs IA ?

---

## 1.2 La Confidentialité Différentielle comme Solution

La **confidentialité différentielle** (Differential Privacy, DP) offre une réponse formelle à cette question. Introduite par Dwork et al. (2006) et formalisée dans Dwork & Roth (2014), la DP garantit mathématiquement qu'un adversaire observant la sortie d'un mécanisme agrégé ne peut pas distinguer si un individu spécifique a participé ou non.

**Définition informelle** : Un mécanisme M satisfait ε-DP si, pour tout individu k et tout ensemble de réponses possibles S :

```
Pr[M(D) ∈ S] ≤ e^ε × Pr[M(D \ {k}) ∈ S]
```

Plus ε est petit, plus la protection est forte. Pour ε = 0.5 (notre choix), un adversaire ne peut pas multiplier sa confiance par plus de e^{0.5} ≈ 1.65 en observant la sortie.

La DP est aujourd'hui déployée dans des systèmes industriels majeurs : Apple (iOS, macOS), Google (RAPPOR, Chrome), la US Census Bureau (recensement 2020). Ces déploiements valident la maturité technologique de l'approche.

---

## 1.3 Limitations des Approches Existantes

Les déploiements industriels actuels souffrent de limitations qui les rendent inadaptés au contexte radio B2B :

**Local DP (Apple, Google)** : Le bruit est ajouté côté client avant transmission. La protection est forte mais l'utilité est faible — il faut des millions d'utilisateurs pour obtenir des agrégats précis. Inadapté aux plateformes radio françaises (quelques millions d'auditeurs au maximum).

**Central DP sans attestation** : Le serveur central applique le bruit après agrégation. L'utilité est meilleure mais le système est vulnérable aux attaques Sybil : un acteur malveillant peut soumettre des milliers de faux signaux et biaiser l'agrégat. Sans mécanisme d'attestation de l'identité des participants, la garantie DP n'est pas opérationnellement valide.

**DP avec flottants IEEE 754** : Les implémentations standard du mécanisme de Laplace sur des flottants double-précision introduisent une fuite d'information via les bits de poids faible (Mironov, 2012). La garantie formelle est (ε, δ)-DP avec δ > 0, pas la pure DP (δ=0).

**Absence de cadre légal explicite** : Les déploiements existants ne documentent pas explicitement leur conformité RGPD ou EU AI Act. Un opérateur radio achetant ces données ne dispose pas de preuve formelle utilisable en cas d'audit réglementaire.

---

## 1.4 Notre Contribution : ANCRE

Nous présentons **ANCRE** (*Attestation & Noise for Confidential Radio Emissions*), un protocole de confidentialité différentielle pure conçu spécifiquement pour le contexte de l'analytics audio B2B.

ANCRE répond aux limitations identifiées par quatre contributions :

**Contribution 1 — Central DP avec haute utilité** : ANCRE applique le bruit côté serveur sur une moyenne tronquée (TMoM, α=0.1), offrant une corrélation de Spearman ρ = 0.9997 avec la vérité terrain sur le dataset Last.fm (92 834 événements, 1 892 utilisateurs).

**Contribution 2 — Attestation SIM IoT SAFE anti-Sybil** : Chaque signal est lié à un certificat X.509 émis par un opérateur télécom de confiance (standard GSMA IoT SAFE, ETSI TS 102 226). Un attaquant Sybil doit contrôler autant de SIM physiques que de faux signaux — économiquement prohibitif.

**Contribution 3 — Pure DP (δ=0) via Laplace discret** : L'implémentation utilise un mécanisme de Laplace discret exact (Ghosh et al., 2012) avec résolution r=1000, éliminant les fuites flottantes de Mironov (2012). La garantie est ε=0.5-DP stricte, sans terme δ.

**Contribution 4 — Traçabilité légale** : Chaque agrégation produit une réponse incluant n (taille du dataset, publié explicitement), ε utilisé, et un hash HMAC-SHA256 de la chaîne d'audit. Ces métadonnées constituent une preuve de conformité RGPD Article 25 (Privacy by Design) et Article 89 (traitements statistiques).

---

## 1.5 Cas d'Usage Cible

**Acteurs** :
- **Plateformes radio** (Radio France, FIP, Mouv', France Inter) : producteurs de données d'écoute.
- **Opérateurs IA** : acheteurs d'agrégats pour entraînement de modèles de recommandation.
- **Régulateurs** (CNIL, DPC) : auditeurs de la conformité RGPD.

**Flux opérationnel** :

```
1. Auditeur écoute → signal brut sur terminal
2. ANCRE client applique bruit LDP (ε_client, couche Python)
3. Signal bruité + attestation SIM → serveur ANCRE
4. Serveur vérifie attestation SIM (anti-Sybil)
5. Fenêtre fermée à K ≥ 100 signaux (K-anonymité)
6. TMoM + DLap discret → agrégat final (ε_server = 0.5)
7. Réponse publiée : résultat + n + ε + hash audit
8. Opérateur IA achète l'agrégat certifié
```

**Modèle économique** : Radio France ne vend plus des données brutes (interdit RGPD) mais des **agrégats DP certifiés**, traçables et auditables. Le prix peut être supérieur aux données brutes car la certification DP réduit le risque légal pour l'acheteur.

---

## 1.6 Organisation du Papier

- **Section 2** : Architecture détaillée du protocole ANCRE.
- **Section 3** : Garanties formelles — Lemme de sensibilité, Théorème ε-DP, Corollaire de composition.
- **Section 4** : Résultats expérimentaux — tests unitaires, KS-test, validation Last.fm, red team multi-IA.
- **Section 5** : Limites, discussion comparative, et travaux futurs.

