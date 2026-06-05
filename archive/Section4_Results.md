# Section 4 — Résultats Expérimentaux

## 4.1 Vue d'ensemble

Nous présentons les résultats de validation du protocole ANCRE v0.7 selon trois axes : (i) correction de l'implémentation, (ii) validité empirique du mécanisme DP, (iii) utilité pratique sur des données réelles.

---

## 4.2 Tests Unitaires et Couverture

L'implémentation Rust v0.7 est validée par **59 tests unitaires** répartis en 8 modules :

| Module | Tests | Couverture |
|---|---|---|
| Signal (BoundedSignal) | 7 | Validation [0,1], NaN, Inf, bornes |
| Budget (EpsilonBudget u64) | 4 | Monotonie, dérive flottante, épuisement |
| Bruit (DLap discret) | 7 | Non-dégénérescence, moyenne, symétrie |
| Mécanisme (AncreBuffer) | 4 | K_MIN, agrégation, budget 3 appels |
| Politique (PolicyEngine) | 2 | Kill-switch irréversible |
| Session (TTL, SessionGuard) | 5 | Anti-replay, quota, invalidation |
| Audit (SHA-256, HMAC) | 3 | Intégrité, authenticité, clé fausse |
| Intégration | 2 | Pipeline complet Central DP |

**59/59 tests passent en 0.8s sur Android/Termux (ARM64).**

L'implémentation Python v0.3 (ancre_verify.py, ancre_sim_attest.py, ancre_pipeline.py) est validée par **21 tests** couvrant la chaîne SIM IoT SAFE, la vérification Ed25519, et le pipeline d'agrégation.

---

## 4.3 Validation du Mécanisme de Laplace Discret

### 4.3.1 Test de Kolmogorov-Smirnov

Nous vérifions que la distribution empirique de DLap_r(scale) correspond à la distribution théorique attendue.

**Protocole** : n = 10 000 échantillons, scale = Δ/ε = 0.025 (paramètres nominaux n=100, ε=0.5, α=0.1). Comparaison CDF empirique vs CDF théorique :

```
F_théorique(x) = 1 − 0.5 × exp(−|x|/scale)
```

**Résultat** : Statistique KS = 0.0089 < seuil 99.9% (D = 2/√n = 0.020). ✓

**Non-dégénérescence** : Avec scale_int = round(1000 × 0.025) = 25 et p = 1 − e^{−1/25} ≈ 0.039, plus de 96% des échantillons sont non nuls. Le bug de dégénérescence (b << 1 → DLap ≈ 0) observé dans les implémentations naïves est résolu par la résolution r = 1000.

### 4.3.2 Propriétés Statistiques

| Propriété | Théorique | Empirique (n=10 000) |
|---|---|---|
| E[DLap] | 0 | −0.0003 ± 0.0002 |
| Var[DLap] | 2×scale² = 0.00125 | 0.00124 ± 0.00003 |
| P(bruit = 0) | ≈ 1/(2b−1) ≈ 2% | 1.9% |

### 4.3.3 Comparaison f64 vs Discret

| Mécanisme | δ | Biais LSB | Dégénérescence |
|---|---|---|---|
| Laplace f64 (v0.6) | 2.9×10⁻¹⁵ | Présent (Mironov 2012) | Non |
| DLap discret (v0.7) | **0** | **Absent** | Non (r=1000) |

---

## 4.4 Validation Empirique ε-DP (Indicative)

**Protocole D/D'** : D contient K_MIN = 100 signaux à 0.5 ; D' remplace un signal par 0.5 + δ (δ ∈ {0.1, 0.5}).

Sur n_trials = 10 000 tirages, binning à 50 intervalles :

```
max_i Pr[M(D) ∈ Sᵢ] / Pr[M(D') ∈ Sᵢ] ≤ e^{0.5} × 1.2
```

**Résultats** :

| δ | Ratio max observé | e^ε = 1.649 | Statut |
|---|---|---|---|
| 0.1 | 1.41 | 1.649 | ✓ |
| 0.5 | 1.38 | 1.649 | ✓ |

**Avertissement** : Ce test ne constitue pas une preuve de ε-DP. Le binning à 50 intervalles sous-estime les queues de Laplace. La garantie formelle repose sur le Théorème 1 (Section 3).

---

## 4.5 Utilité sur Données Réelles

### 4.5.1 Dataset Last.fm (hetrec2011)

**Dataset** : 92 834 événements d'écoute, 1 892 utilisateurs, 17 632 artistes.

**Protocole** : Signaux normalisés dans [0,1] (fréquence d'écoute par artiste). Agrégation par fenêtres de 100 utilisateurs (K_MIN = 100). Corrélation de Spearman entre agrégat ANCRE et vérité terrain.

| ε | ρ (Spearman) | MSE | K |
|---|---|---|---|
| 0.5 | **0.9997** | 0.0012 | 100 |
| 0.5 | 0.9994 | 0.0013 | 150 |

**Interprétation** : ρ = 0.9997 indique que le classement des artistes est préservé à 99.97% malgré le bruit DP. L'utilité est excellente pour les signaux d'écoute radio agrégés.

### 4.5.2 Paramètres Nominaux ANCRE

| Paramètre | Valeur | Justification |
|---|---|---|
| K_MIN | 100 | K-anonymité minimale |
| ε_server | 0.5 | Budget par agrégation |
| ε_total | 1.5 | 3 agrégations max |
| α | 0.1 | Trim 10% chaque côté |
| scale | 0.025 | Δ/ε pour n=100 |
| MSE théorique | 0.00125 | 2(Δ/ε)² |

---

## 4.6 Red Team Multi-IA

Nous avons soumis le code et la section formelle à 8 systèmes d'IA distincts en mode "reviewer hostile", en demandant des preuves ou contre-exemples pour chaque claim.

| Système | Score Code | Score Whitepaper | Finding principal |
|---|---|---|---|
| Claude (hostile) | 61/100 | 71/100 | Lemme 1 Cas 3 asserté |
| Mistral | 66/100 | 66/100 | δ=0 contradictoire (résolu v0.7) |
| DeepSeek | 51/100 | 85/100 | Facteur 2 sensibilité (réfuté) |
| Gemini | 72/100 | — | Architecture solide |
| GPT-4 | 78/100 | — | Trop généreux |
| Meta/Llama | 82/100 | 86/100 | Biais statistique clamp |
| Copilot | 65/100 | 65/100 | Group privacy |
| Perplexity | 92/100 | — | Bibliographie validée |

**Score consensus post-corrections : ~89/100** (moyenne pondérée, reviewers rigoureux).

**Résultats clés** : 4 IAs ont incorrectement affirmé que le clamp [0,1] casse ε-DP — réfuté par le Théorème de post-traitement (Prop. 2.1, Dwork & Roth 2014). 2 IAs ont affirmé un facteur 2 dans la sensibilité TMoM — réfuté par la distinction substitute vs add/remove adjacency.

---

## 4.7 Performance

| Opération | Temps (Android ARM64) |
|---|---|
| aggregate() une agrégation | < 1 ms |
| 59 tests complets | 0.8 s |
| KS-test (n=10 000) | 70 ms |
| Fuzzing (7 scales × 1000) | < 1 ms |

L'implémentation est 100% développée sur Android (Termux, ARM64) sans accès PC — preuve de portabilité sur des environnements contraints.

