# Section 2 — Architecture du Protocole ANCRE

## 2.1 Vue d'Ensemble

ANCRE est un protocole en trois couches, chacune avec des responsabilités distinctes :

```
┌─────────────────────────────────────────────────┐
│  Couche 1 : Client (terminal auditeur)           │
│  ancre_pipeline.py — Bruit LDP + Attestation SIM │
└────────────────────┬────────────────────────────┘
                     │ Signal bruité + Attestation
┌────────────────────▼────────────────────────────┐
│  Couche 2 : Serveur ANCRE (Central DP)           │
│  ancre_verify.py + ancre-rust-v07/              │
│  Vérification SIM, TMoM, DLap, Budget            │
└────────────────────┬────────────────────────────┘
                     │ Agrégat certifié
┌────────────────────▼────────────────────────────┐
│  Couche 3 : Opérateur IA                         │
│  Consommateur d'agrégats DP certifiés            │
└─────────────────────────────────────────────────┘
```

Les garanties DP opèrent principalement en Couche 2 (Central DP). La Couche 1 ajoute une couche LDP optionnelle (ε_client = 1.0) et l'attestation SIM anti-Sybil.

---

## 2.2 Couche 1 — Client ANCRE

### 2.2.1 Validation du Signal

Chaque signal brut est validé avant tout traitement :

```python
def validate_signal(signal: float) -> float:
    # Rejet NaN, Inf, valeurs hors [0,1]
    # Hypothèse H2 : signaux bornés dans [0,1]
```

Les signaux d'écoute sont normalisés dans [0,1] (ex. : durée d'écoute / durée maximale de la fenêtre).

### 2.2.2 Bruit LDP Client (optionnel)

Un bruit Laplace discret est appliqué côté client (ε_client = 1.0, Δ_client = 1) :

```
noisy = clamp(raw_signal + DLap(1.0/ε_client), 0, 1)
del raw_signal  # destruction du signal brut
```

Cette couche LDP réduit la confiance requise envers le serveur : même un serveur compromis ne voit que des signaux déjà bruités.

### 2.2.3 Attestation SIM IoT SAFE

Chaque signal bruité est signé par la clé Ed25519 stockée dans la SIM du terminal :

```
payload = {signal_hash, nonce, slot, sim_mode, timestamp_utc}
signature = SIM.sign(SHA256(payload))
attestation = (noisy_value, payload, signature, certificate_chain)
```

La SIM produit un certificat X.509 auto-signé (développement) ou signé par l'opérateur télécom (production). Le `signal_hash` est un SHA-256 du signal via `struct.pack('>d', value)` — encodage IEEE 754 déterministe sur toutes les plateformes.

---

## 2.3 Couche 2 — Serveur ANCRE

### 2.3.1 Vérification de l'Attestation (ancre_verify.py v0.3)

L'ordre de vérification est critique pour la sécurité :

```
1. Taille certificat    ← guard DoS avant parse
2. Signal valide        ← guard NaN/Inf
3. Reject mock          ← politique production
4. Parse certificat DER ← nécessaire pour clé publique
5. Expiry certificat    ← validité temporelle
6. Opérateur autorisé   ← politique PKI
7. CA chain             ← confiance racine
8. SIGNATURE ED25519    ← avant nonce et quota (V1)
9. Fraîcheur timestamp  ← fenêtre ±300s
10. Anti-replay nonce   ← consommé après signature valide
11. Hash signal         ← cohérence signal/payload
12. Quota device        ← max 1 signal/SIM/fenêtre (H1)
```

**V1 — Signature avant nonce** : Un attaquant avec une fausse signature ne peut pas consommer des nonces ou des quotas. L'inversion de l'ordre (signature après nonce) permettrait une attaque par épuisement de ressources.

**V2 — Ed25519 sans hash séparé** : L'API cryptography Python requiert `.verify(sig, data)` sans algorithme de hash pour Ed25519 (contrairement à RSA/ECDSA). L'erreur v0.2 retournait `False` silencieusement pour tous les certificats Ed25519.

### 2.3.2 Buffer et Fenêtre d'Agrégation

Les signaux validés sont accumulés dans un buffer thread-safe :

```
Buffer : [(noisy_value, cert_serial), ...]
Limite : MAX_BUFFER_SIZE = 10 000 signaux
Timeout : BUFFER_TIMEOUT_SEC = 3600s
```

La fenêtre est fermée (H6) lorsque K ≥ K_MIN = 100 signaux sont disponibles et que l'opérateur appelle `aggregate()`. Cette fermeture explicite justifie le modèle substitute adjacency.

### 2.3.3 Mécanisme d'Agrégation ANCRE (ancre-rust-v07)

L'agrégation est implémentée en Rust pour la performance et la sécurité mémoire :

**Étape 1 — Déduplication Sybil** :
```
filtered = {serial → noisy_value : un signal par device}
k_filtered = len(filtered) ≥ K_MIN
```

**Étape 2 — TMoM_α (Lemme 1)** :
```
sorted_vals = sort(filtered.values())  # tri stable total_cmp
trim = floor(α × n)
center = sorted_vals[trim : n-trim]
tmom = sum(center) / n_eff   # n_eff = n - 2×trim
```

Convention tie-breaking : `total_cmp` sur f64 (Rust) ou TimSort stable (Python), ordre lexicographique sur les indices en cas d'ex-aequo. T(D) est uniquement défini (Lemme 1, Cas 3).

**Étape 3 — DLap discret (Théorème 1)** :
```
Δ = 1/n_eff                     # sensibilité formelle
scale = Δ/ε                     # ε = EPSILON_SERVER = 0.5
scale_int = round(r × scale)    # r = 1000, scale_int = 25
k ~ DLap(scale_int)             # G1 - G2, Gi ~ Geom(p)
noise = k / r                   # retour en domaine [0,1]
```

**Étape 4 — Post-traitement** :
```
result = clamp(tmom + noise, 0.0, 1.0)
```

**Étape 5 — Réponse (H3)** :
```rust
AggregateResponse {
    result: f64,           // agrégat final
    n: usize,              // publié explicitement
    epsilon_used: f64,     // ε consommé
    delta_bound: f64,      // 0.0 pour DLap discret
    total_epsilon_used: f64,
}
```

---

## 2.4 Budget ε et Kill-Switch

### 2.4.1 EpsilonBudget (u64)

Le budget est tracké en micro-epsilon (u64) pour éviter la dérive flottante cumulative :

```
1.0 ε = 1_000_000 μ-ε
EPSILON_MAX = 1.5 → 1_500_000 μ-ε
```

L'opération `spend(0.5)` est atomique — elle échoue sans modifier l'état si le budget est insuffisant. Trois agrégations exactes sont possibles, pas quatre.

### 2.4.2 Kill-Switch (PolicyEngine)

```rust
killed: Arc<AtomicBool>  // Release/Acquire ordering
```

Le kill-switch est irréversible (Ordering::Release sur `store(true)`, Ordering::Acquire sur `load()`). Une fois activé, toutes les opérations `push()` et `aggregate()` retournent une erreur.

### 2.4.3 SessionGuard

Chaque credential est lié à un `SessionGuard` qui invalide définitivement la session après épuisement du budget :

```rust
if aggregation_count >= max_aggregations {
    self.invalidated = true;  // irréversible
    return Err("Session invalidée");
}
aggregation_count += 1;
```

La vérification est faite AVANT l'incrément pour éviter un décalage off-by-one.

---

## 2.5 Chaîne d'Audit

Chaque agrégation est enregistrée dans une chaîne d'audit HMAC-SHA256 :

```
entry_i = HMAC(key, prev_hash || agg || k || ε)
```

La chaîne est append-only — une modification d'une entrée invalide toutes les suivantes. La clé HMAC est partagée entre la plateforme et l'opérateur IA, permettant une vérification a posteriori en cas d'audit RGPD.

---

## 2.6 Ancrage Temporel RFC3161

La preuve de concept ANCRE est ancrée temporellement via le serveur FreeTSA (RFC3161) :

```
anchor_hash    : 13a7d636...
token_sha256   : 938559cb...
anchored_at    : 2026-03-31T21:01:11 UTC
```

Cet ancrage prouve l'antériorité du protocole indépendamment de la date de publication arXiv.

---

## 2.7 Invariants du Protocole

Les paramètres suivants sont non modifiables dans la version courante :

| Paramètre | Valeur | Rôle |
|---|---|---|
| K_MIN | 100 | K-anonymité, kill-switch |
| EPSILON_SERVER | 0.5 | Budget par agrégation |
| EPSILON_MAX | 1.5 | Budget total (3 agrégations) |
| TRIM_FRACTION | 0.1 | Robustesse TMoM |
| DISCRETE_RESOLUTION | 1000 | Précision DLap |
| MAX_BUFFER_SIGNALS | 10 000 | Limite mémoire |
| NONCE_TTL_SECS | 300 | Fenêtre anti-replay |

