# ANCRE — Section Formelle
## Garanties de Confidentialité Différentielle

**Version** : 0.5  
**Auteur** : SAS VERA / ANCRE  
**Date** : Mai 2026

---

## 1. Modèle et Hypothèses

### 1.1 Modèle d'adversaire

Nous adoptons le modèle **Central DP** (McSherry, SIGMOD 2009) :

- Un serveur de confiance collecte les signaux bruts des participants.
- L'adversaire observe uniquement la sortie agrégée publiée.
- L'adversaire est **semi-honnête** : il suit le protocole mais tente d'inférer des informations sur les participants individuels à partir des sorties.

### 1.2 Définition — ε-Differential Privacy

**Définition 2.4** (Dwork & Roth, 2014) :

Un mécanisme randomisé M : D → R satisfait **ε-DP** si pour tout couple de datasets D, D' adjacents (différant d'exactement un individu) et pour tout sous-ensemble S ⊆ R :

```
Pr[M(D) ∈ S] ≤ exp(ε) × Pr[M(D') ∈ S]
```

### 1.3 Hypothèses du Système

**H1 — Un individu = un signal par session.**  
Chaque participant contribue au plus un signal par fenêtre d'agrégation. La couche d'attestation SIM IoT SAFE (ANCRE Python) impose cette contrainte via les certificats d'opérateur télécom.

**H2 — Signaux bornés.**  
Tout signal appartient à [0, 1]. La structure `BoundedSignal` impose cette contrainte au niveau du type.

**H3 — K-anonymité.**  
Une agrégation nécessite K ≥ K_MIN = 100 signaux. En dessous de ce seuil, aucune sortie n'est publiée.

---

## 2. Mécanisme ANCRE

Le mécanisme ANCRE par agrégation est défini comme suit :

```
M_ANCRE(D) = clamp(TMoM(D) + Lap(Δ/ε), 0, 1)
```

où :
- **TMoM(D)** = Trimmed Mean of Means avec α = 0.1 (10% trim)
- **Δ** = sensibilité globale de TMoM sur D
- **ε** = ε_server = 0.5
- **Lap(b)** = variable aléatoire de loi de Laplace centrée, d'échelle b
- **clamp** = post-traitement déterministe dans [0, 1]

---

## 3. Lemme 1 — Sensibilité du Trimmed Mean

**Lemme 1.**  
*Soit D un dataset de n signaux dans [0, 1], avec n ≥ 100 et α = 0.1. La sensibilité globale L1 de la moyenne tronquée TMoM est :*

```
Δ(TMoM) = 1 / (n × (1 - 2α)) = 1 / (0.8n)
```

**Preuve.**

Soient D = {x₁, ..., xₙ} et D' = {x₁, ..., xₙ} différant d'exactement un élément (x_i → x'_i).

Après tri et suppression des α×n valeurs inférieures et supérieures, la moyenne tronquée porte sur n_eff = n × (1 - 2α) = 0.8n éléments.

**Cas 1** : x_i est dans la région tronquée (queue inférieure ou supérieure).  
La modification ne change aucun élément de la somme tronquée.  
→ |TMoM(D) - TMoM(D')| = 0 ≤ Δ ✓

**Cas 2** : x_i est dans la région conservée (80% central).  
La modification change la somme d'au plus |x'_i - x_i| ≤ 1 (car signaux dans [0,1]).  
La moyenne change d'au plus 1/n_eff = 1/(0.8n).  
→ |TMoM(D) - TMoM(D')| ≤ 1/(0.8n) = Δ ✓

**Cas 3** : La modification déplace x_i de la queue vers la région centrale (ou vice versa).  
Le pire cas : un élément de valeur 0 entre dans la région centrale avec valeur 1.  
La variation maximale de la somme reste bornée par 1.  
→ |TMoM(D) - TMoM(D')| ≤ 1/(0.8n) = Δ ✓

Dans tous les cas, |TMoM(D) - TMoM(D')| ≤ 1/(0.8n).  
**□**

**Référence** : Steinke & Ullman, "Private Robust Statistics" (arXiv:2006.07327), Lemma 3.1.

---

## 4. Théorème Principal — ε-DP de M_ANCRE

**Théorème 1.**  
*Sous les hypothèses H1, H2, H3, le mécanisme M_ANCRE est ε_server = 0.5-DP par appel à aggregate().*

**Preuve.**

**Étape 1 — Mécanisme de Laplace.**

Par le Lemme 1, Δ(TMoM) = 1/(0.8n).

Le mécanisme M₀(D) = TMoM(D) + Lap(Δ/ε_server) est ε_server-DP par application du **Théorème 3.6** (Dwork & Roth, 2014) :

```
Pr[M₀(D) ∈ S] / Pr[M₀(D') ∈ S]
≤ exp(|TMoM(D) - TMoM(D')| / (Δ/ε))
≤ exp(Δ / (Δ/ε))
= exp(ε)
```

**Étape 2 — Post-traitement (clamp).**

La fonction clamp(·, 0, 1) est déterministe et ne dépend pas de D.

Par la **Proposition 2.1** (Dwork & Roth, 2014) — Théorème de Post-traitement :

> *Si M est ε-DP et f est une fonction déterministe, alors f ∘ M est ε-DP.*

Donc M_ANCRE = clamp ∘ M₀ est ε_server = 0.5-DP.  
**□**

---

## 5. Corollaire — Composition Séquentielle

**Corollaire 1.**  
*Sur un lifetime budget de EPSILON_MAX = 1.5, ANCRE permet au plus 3 agrégations indépendantes, chacune 0.5-DP, pour une perte totale ε_total ≤ 1.5 par composition séquentielle.*

**Preuve.**

Par la **Proposition 3.14** (Dwork & Roth, 2014) — Composition séquentielle :

Si M₁ est ε₁-DP et M₂ est ε₂-DP sur des datasets indépendants, alors (M₁, M₂) est (ε₁ + ε₂)-DP.

ANCRE exécute au plus k = EPSILON_MAX / EPSILON_SERVER = 3 agrégations.  
ε_total = 3 × 0.5 = 1.5 = EPSILON_MAX.  
Le kill-switch `EpsilonBudgetExact` enforce cette borne au niveau du type (u64).  
**□**

---

## 6. Limites et Discussion

### 6.1 Hypothèse "1 individu = 1 signal"

La garantie ε-DP est **par signal**, pas nécessairement par individu si un individu peut contribuer plusieurs signaux via plusieurs credentials (attaque Sybil).

**Mitigation** : La couche ANCRE Python avec attestation SIM IoT SAFE lie chaque signal à une identité télécom certifiée, imposant H1 en pratique.

### 6.2 Nonces TTL

Le cache nonce avec TTL=300s protège contre le replay dans la fenêtre temporelle. Un nonce peut être réutilisé après expiration — limitation documentée et acceptable pour le cas d'usage radio analytics.

### 6.3 Post-traitement et Utilité

Le clamp [0,1] préserve la garantie ε-DP (Proposition 2.1) mais introduit un biais aux bornes. Pour des signaux dans (0.1, 0.9), l'impact est négligeable. Ce compromis est documenté.

---

## 7. Références

```
[1] Dwork, C. & Roth, A. (2014). "The Algorithmic Foundations of 
    Differential Privacy". Foundations and Trends in TCS.
    → Définition 2.4, Proposition 2.1, Théorème 3.6, Proposition 3.14

[2] Steinke, T. & Ullman, J. (2020). "Private Robust Statistics".
    arXiv:2006.07327.
    → Lemme 3.1 : sensibilité TMoM

[3] McSherry, F. (2009). "Privacy Integrated Queries".
    ACM SIGMOD 2009.
    → Modèle Central DP

[4] Abadi, M. et al. (2016). "Deep Learning with Differential Privacy".
    ACM CCS 2016.
    → Trimmed means en pratique

[5] Erlingsson, Ú. et al. (2018). "Amplification by Shuffling".
    arXiv:1811.03853.
    → Contexte fédéré
```

---

*Cette section constitue la base formelle du protocole ANCRE v0.5.  
Elle est destinée à être intégrée dans le whitepaper VERA/ANCRE  
et dans un preprint soumis à arXiv cs.CR.*
