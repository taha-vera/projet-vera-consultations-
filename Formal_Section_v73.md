# ANCRE — Section Formelle v7.3
## Garanties de Confidentialité Différentielle

**Version** : 0.7.1  
**Auteur** : SAS VERA / ANCRE  
**Date** : Mai 2026  
**Statut** : Draft preprint — corrections post-reviews Claude v7.2 (71/100)

---

## 1. Modèle et Hypothèses

### 1.1 Modèle d'adversaire

Nous adoptons le modèle **Central DP** (McSherry, SIGMOD 2009) avec un adversaire **semi-honnête (honest-but-curious)** :

- Le serveur de confiance collecte les signaux bruts.
- L'adversaire observe la sortie agrégée M(D) et les métadonnées publiées (n, ε).
- Le Laplace discret exact élimine les fuites LSB — pas de canal via la variance flottante.

**Hors modèle** : canaux auxiliaires timing O(n log n), attaques Sybil (§6.1).

### 1.2 Définitions préliminaires

**Définition 1 — Substitute Adjacency (~_s)** :
D ~_s D' si |D| = |D'| = n et D' = (D \ {x_k}) ∪ {x'_k} pour un indice k.

**Définition 2 — Add/Remove Adjacency (~_ar)** :
D ~_ar D' si |D △ D'| = 1.

**Avantage ~_s** : n et n_eff sont constants entre D et D'. Sous ~_ar, n_eff varie et la sensibilité devient 2/n_eff.

**Définition 3 — ε-DP pure (δ=0)** (Dwork & Roth, 2014, Déf. 2.4) :

M satisfait ε-DP si pour tout D ~_s D' et tout S ⊆ R :

```
Pr[M(D) ∈ S] ≤ exp(ε) × Pr[M(D') ∈ S]
```

### 1.3 Hypothèses

**H1** — Un individu = un signal par session. Imposé par le protocole SIM IoT SAFE et la contrainte `max_per_device = 1` (ancre_pipeline.py v0.3, C5).

**H2** — Signaux bornés dans [0,1] (type `BoundedSignal` Rust, `validate_signal()` Python).

**H3** — n publié dans `AggregateResponse.n` avant la sortie agrégée, selon l'ordre atomique :
1. Calculer n = |D|
2. Écrire n dans la réponse
3. Si n < K_MIN → renvoyer ⊥

L'adversaire connaît n indépendamment du kill-switch (Dwork & Roth §3.5).

**H4** — Indépendance ChaCha20 (Rust) / secrets.SystemRandom (Python). Hypothèse de confiance architecturale. **Non requise pour la garantie DP du mécanisme.**

**H5** — Population fixe pour la composition. Un individu absent de l'agrégation i n'est pas affecté par M_i (Claim 3.16, Dwork & Roth §3.5).

**H5a** — Paramètres homogènes pour toutes les agrégations (α, ε, n identiques).

**H6 — Fenêtre fermée** : La fenêtre de collecte est fermée et n fixé **avant** l'appel à aggregate(). Cette hypothèse justifie l'application du modèle ~_s au système ANCRE : une fois la fenêtre fermée, toute paire (D, D') dans le raisonnement DP a |D| = |D'| = n par construction.

Note : H6 ne définit pas ~_s (qui est purement mathématique) — elle justifie que le contexte physique correspond à cette définition.

### 1.4 Mécanisme de Laplace Discret Exact

**Algorithme** (Ghosh, Roughgarden & Sundararajan, 2012 ; Canonne, Kamath & Steinke, 2020) :

```
DLap(scale_int) = G₁ − G₂,  Gᵢ ~ Geom(p)
p = 1 − exp(−1/scale_int)
```

**Résolution r = 1000** pour le domaine [0,1] :
```
scale_int = round(r × Δ/ε) = round(1000 × 0.025) = 25
noise = DLap(scale_int) / r ∈ {k/1000 : k ∈ ℤ}
```

Pour scale_int = 25 : p ≈ 0.039 — bruit non dégénéré (b ≈ 0.025, non nul).

**Pure DP (δ=0)** : Le Laplace discret opère sur une grille finie, éliminant les fuites LSB des implémentations flottantes (Mironov, 2012). La garantie ε-DP est stricte, sans terme additif δ.

---

## 2. Mécanisme ANCRE

```
M_ANCRE(D) = clamp(TMoM_α(D) + DLap_r(Δ/ε), 0, 1)
```

- **TMoM_α** : moyenne tronquée, α = 0.1
- **Δ** = 1/n_eff = 1/(n×0.8) (Lemme 1, substitute adjacency)
- **DLap_r** : Laplace discret, résolution r=1000, ε = 0.5
- **clamp** : post-traitement indépendant des données

**Borne d'utilité (MSE)** :

Pour μ = TMoM_α(D) ∈ (Δ/ε, 1−Δ/ε) :

```
MSE ≈ 2(Δ/ε)² = 2/(n_eff × ε)²
```

Pour n=100, ε=0.5 : MSE ≈ 2×(0.025)² = 0.00125.

Comparaison : moyenne simple sans trim → MSE = 2×(1/(nε))² = 0.0008. Le trim introduit un facteur (1/0.8)² ≈ 1.56, justifié par la robustesse aux outliers (Dwork & Lei, 2009).

---

## 3. Lemme 1 — Sensibilité du TMoM (Substitute Adjacency)

**Lemme 1.**
*Soit D = {x₁,...,xₙ}, xᵢ ∈ [0,1], n ≥ 100, α = 0.1. Sous ~_s :*

```
Δ_subst(TMoM_α) ≤ 1/(n × 0.8)
```

**Préliminaire — n_eff ≥ 0.8n** : Pour n ≥ 100, n_eff = n − 2⌊0.1n⌋ ≥ 0.8n. ✓

**Convention tie-breaking** : En cas d'ex-aequo à la frontière du trim, l'ordre est déterminé par l'index dans le tableau trié (tri stable — TimSort en Python, total_cmp en Rust). T(D) est ainsi uniquement défini pour tout D.

**Notation** : T(D) = indices retenus après trim (positions ⌊αn⌋+1 à n−⌊αn⌋ dans le tri stable de D). |T(D)| = n_eff constant sous ~_s (H6).

```
TMoM_α(D) = (1/n_eff) × Σ_{i ∈ T(D)} x_{(i)}
```

**Preuve.**

Soient D ~_s D' : D' = D avec x_k → x'_k, x_k, x'_k ∈ [0,1].

**Cas 1** — x_k ∉ T(D) et x'_k ∉ T(D') : Δ_somme = 0. ✓

**Cas 2** — x_k ∈ T(D) et x'_k ∈ T(D') : Δ_somme = x'_k − x_k, |Δ_somme| ≤ 1. ✓

**Cas 3** — Transition queue/centre.

**Lemme auxiliaire** : Sous ~_s avec tri stable et convention tie-breaking par index, une substitution x_k → x'_k déplace au plus **une** position de frontière.

*Preuve du Lemme auxiliaire* : La substitution modifie exactement un élément du tableau trié. Dans le tri stable, si x_k passe d'une queue (position ≤ ⌊αn⌋) au centre ou vice versa, exactement un index frontière change de côté (l'index ⌊αn⌋ ou n−⌊αn⌋). En cas d'ex-aequo, la convention tie-breaking par index garantit que la frontière ne "saute" pas de plusieurs positions simultanément. Donc |T(D) △ T(D')| ≤ 2.

Sous ce lemme, soit f la valeur entrant dans T(D'), e la valeur sortant de T(D). f, e ∈ [0,1] :

```
|f − e| ≤ 1   (bornitude de [0,1])
```

Note fondamentale : |f − e| est une différence signée ≤ 1, pas une somme d'absolus (+1 + 1 = 2). C'est la distinction critique avec ~_ar.

|TMoM(D) − TMoM(D')| = |f − e|/n_eff ≤ 1/(0.8n). ✓

**Vérification numérique** : D = [0×10, 0.5×80, 1×10], D' remplace un 0 par 1 → |ΔTMoM| = 1/160 < 1/80. ✓

Dans tous les cas, Δ_subst ≤ 1/(0.8n). **□**

---

## 4. Théorème Principal — ε-DP de M_ANCRE

**Théorème 1.**
*Sous H1, H2, H6 et substitute adjacency, M_ANCRE satisfait ε = 0.5-DP (pure DP, δ=0) par appel à aggregate().*

**Étape 1 — Mécanisme de Laplace discret.**

Par Lemme 1, Δ ≤ 1/(0.8n) sous ~_s.

M₀(D) = TMoM_α(D) + DLap_r(Δ/ε) satisfait ε-DP par le **Théorème du mécanisme de Laplace discret** :

*Si f : D → ℝ a sensibilité Δ et M(D) = f(D) + DLap(Δ/ε), alors M satisfait ε-DP.*

Référence : Ghosh, Roughgarden & Sundararajan (2012), Theorem 1 — applicable au mécanisme de Laplace discret avec sensibilité Δ et scale Δ/ε. Pure DP (δ=0) par construction de DLap.

**Étape 2 — Post-traitement.**

f(x) = clamp(x, 0, 1) est une fonction déterministe indépendante des données.

Par Proposition 2.1 (Dwork & Roth, 2014) :

```
M_ANCRE = f ∘ M₀  satisfait  ε = 0.5-DP (δ=0).  □
```

**Note** : H3, H4, H5 ne sont pas requises pour cette garantie.

---

## 5. Corollaire — Composition Séquentielle

**Corollaire 1.**
*Sous H1, H3, H5, H5a, avec n_i ≥ 100 et paramètres homogènes, ANCRE permet au plus k = 3 agrégations :*

```
ε_total = k × 0.5 = 1.5   (pure DP)
δ_total = 0                (DLap exact)
```

**Preuve.** Par Prop. 3.14 (Dwork & Roth) — composition pure DP, sans hypothèse d'indépendance. Sous H5 et Claim 3.16 : individu absent → non affecté. `EpsilonBudget` (u64) enforce ε_total ≤ 1.5. **□**

---

## 6. Limites

**6.1 Sybil** — j contributions → j×ε-DP (Prop. 2.2). Mitigation : SIM IoT SAFE + `max_per_device=1` (H1 stricte).

**6.2 Timing** — Tri O(n log n) data-dépendant. Non couvert.

**6.3 Substitute adjacency et sessions radio** — H6 justifie ~_s si la fenêtre est fermée avant agrégation. Si n fluctue pendant la fenêtre, ~_ar s'applique et Δ = 2/(0.8n).

**6.4 Clamp aux bornes** — Biais statistique E[M_ANCRE(D)] ≠ TMoM_α(D) pour μ ∈ [0, Δ/ε] ∪ [1−Δ/ε, 1]. Garantie ε-DP préservée.

---

## 7. Évaluation Empirique (Indicative)

59 tests unitaires (ANCRE Rust v0.7) + 21 tests Python v0.3.

**Protocole D/D'** : D contient K_MIN=100 signaux à 0.5, D' remplace un signal par 0.5+δ (δ ∈ {0.1, 0.5}). Le ratio empirique Pr[M(D)∈S]/Pr[M(D')∈S] est estimé sur 10 000 tirages avec binning à 50 intervalles.

**KS-test** : Distribution empirique de DLap comparée à la CDF théorique, seuil 99.9% (D=2/√n ≈ 0.02 pour n=10 000).

**Avertissement** : Ces tests ne constituent pas une preuve de ε-DP. Le binning à 50 intervalles sous-estime les queues de Laplace où exp(ε) est maximal.

---

## 8. Références

```
[1] Dwork, C. & Roth, A. (2014). "Algorithmic Foundations of DP".
    Foundations and Trends in TCS.
    → Déf. 2.4, Prop. 2.1/2.2/3.14, Thm. 3.6, §3.5, Claim 3.16

[2] Ghosh, A., Roughgarden, T. & Sundararajan, M. (2012).
    "Universally Utility-Maximizing Privacy Mechanisms".
    SIAM Journal on Computing 41(6).
    → Theorem 1 : mécanisme de Laplace discret, garantie ε-DP pure

[3] Canonne, C., Kamath, G. & Steinke, T. (2020).
    "The Discrete Gaussian for Differential Privacy". NeurIPS 2020.
    → Section 2 : DLap et propriétés DP discrètes

[4] McSherry, F. (2009). "Privacy Integrated Queries". ACM SIGMOD.
    → Modèle Central DP

[5] Dwork, C. & Lei, J. (2009). "DP and Robust Statistics". ACM STOC.
    → Sensitivity analysis TMoM

[6] Mironov, I. (2012). "On Significance of the LSB for DP".
    ACM CCS 2012.
    → LSB leakage — résolu par DLap exact (v0.7)

[7] Kairouz, P. et al. (2021). "Advances and Open Problems in
    Federated Learning". JMLR 22(1).
    → Problèmes ouverts DP fédéré (§6)
```

---

*ANCRE v0.7.1 — Section formelle v7.3.*
*Corrections v7.3 : référence DLap → Ghosh 2012 (Theorem 1 explicite),*
*Canonne 2020 maintenu pour contexte discret général,*
*Lemme auxiliaire Cas 3 formalisé (tie-breaking + une frontière),*
*H6 reformulée (justification physique, pas circulaire),*
*H5a justifiée dans Corollaire 1,*
*Protocole D/D' décrit explicitement §7.*
