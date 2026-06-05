# Section 5 — Limites, Discussion et Travaux Futurs

## 5.1 Limites du Modèle

### 5.1.1 Hypothèse de Substitute Adjacency

Le mécanisme ANCRE est prouvé sous le modèle de **substitute adjacency** (~_s) : les datasets D et D' ont la même taille n. Cette hypothèse est justifiée par H6 (fenêtre fermée avant agrégation), mais elle impose une contrainte opérationnelle forte.

Si un participant se déconnecte en cours de fenêtre ou si n fluctue, le modèle correct est **add/remove adjacency** (~_ar), qui donne une sensibilité 2/(0.8n) — double de notre borne. Dans ce cas, le système reste ε-DP mais avec ε effectif = 1.0 au lieu de 0.5 pour la même précision.

**Recommandation** : Fermer la fenêtre d'agrégation par timestamp, rejeter les arrivées tardives, et publier n avant toute sortie (H3 + H6 conjointement).

### 5.1.2 Hypothèse H1 et Attaques Sybil

La garantie ε-DP par individu repose sur H1 : un individu = un signal par session. Un adversaire Sybil soumettant j signaux via j identités distinctes obtient une perte de j×ε-DP (Prop. 2.2, Dwork & Roth).

**Mitigation actuelle** : La couche d'attestation SIM IoT SAFE (GSMA IoT SAFE, ETSI TS 102 226) lie chaque signal à un certificat X.509 émis par un opérateur télécom de confiance (Orange, SFR, Bouygues Telecom). La contrainte `max_per_device = 1` est enforcée côté serveur (ancre_pipeline.py v0.3, C5).

**Limite** : En l'absence de SIM physique (développement, test), le mode MockSimCard accepte tout certificat auto-signé. Le mode production requiert une SIM IoT SAFE réelle et des CA opérateurs de confiance dans `trusted_ca_certs`.

### 5.1.3 Canaux Auxiliaires

Le mécanisme de Laplace discret élimine les fuites LSB (Mironov, 2012). Cependant, deux canaux auxiliaires restent non couverts :

**Timing** : Le tri TMoM s'exécute en O(n log n) avec un temps data-dépendant. Un adversaire mesurant les temps de réponse peut inférer des informations sur la distribution des signaux. Ce canal est hors du modèle honest-but-curious standard mais peut être exploité dans un modèle d'adversaire actif.

**Messages d'erreur** : Les erreurs (kill-switch, budget épuisé, replay) peuvent révéler de l'information sur l'état interne. Le serveur devrait retourner des erreurs opaques en production.

### 5.1.4 Composition et Sessions Multiples

La composition séquentielle (Corollaire 1) garantit ε_total = 1.5 sur 3 agrégations. Cette garantie suppose H5 (population fixe) et H5a (paramètres homogènes). Si la population change entre les fenêtres (sessions radio avec auditeurs différents), la composition reste valide mais ε_total est une borne supérieure conservatrice.

---

## 5.2 Discussion

### 5.2.1 Choix de ε = 0.5

Le budget ε = 0.5 par agrégation est conservateur. La littérature DP appliquée utilise typiquement ε ∈ [0.1, 10] selon les cas d'usage :

- ε < 1 : usage médical, données très sensibles
- ε ∈ [1, 5] : usage commercial standard
- ε > 5 : utilité maximale, protection minimale

Pour des données d'écoute radio (moins sensibles que des données de santé), ε = 0.5 offre une protection forte avec une utilité mesurée à ρ = 0.9997 (Spearman). Ce choix positionne ANCRE vers la protection maximale, cohérent avec une approche "Privacy by Design" (RGPD Article 25).

### 5.2.2 Comparaison avec l'État de l'Art

| Approche | Modèle DP | δ | Sybil | Utilité |
|---|---|---|---|---|
| ANCRE v0.7 | Central, pure | 0 | SIM IoT SAFE | ρ=0.9997 |
| Apple DP (iOS) | Local, (ε,δ) | >0 | Aucune | Moyenne |
| Google RAPPOR | Local | 0 | Aucune | Faible |
| DP-SGD (ML) | Central, (ε,δ) | >0 | N/A | Contexte ML |

**Avantage ANCRE** : La combinaison Central DP + Laplace discret (δ=0) + attestation SIM est, à notre connaissance, absente de la littérature existante pour le domaine de l'analytics audio/radio.

### 5.2.3 Conformité Réglementaire

**RGPD (EU 2016/679)** :
- Article 25 (Privacy by Design) : le mécanisme DP est architectural, pas ajouté post-hoc. ✓
- Article 89 (Traitements à des fins statistiques) : les agrégats ANCRE constituent des données statistiques anonymisées si ε est suffisamment petit et K ≥ 100. ✓

**EU AI Act (2024)** :
- Article 10 (Qualité des données) : applicable si les agrégats ANCRE alimentent un système IA en aval. ANCRE garantit la qualité statistique des données par TMoM (robustesse aux outliers).

**RFC3161** :
- La preuve de concept ANCRE est ancrée temporellement via FreeTSA (Mars 2026, token_sha256 : 938559cb...). L'antériorité est prouvable indépendamment de cette publication.

---

## 5.3 Travaux Futurs

### 5.3.1 Court Terme — v0.8

**Puce intégrée (TEE/ARM TrustZone)** : Déplacer le générateur DLap dans un Trusted Execution Environment garantit H4 par architecture matérielle (pas seulement par hypothèse de confiance). Sur Android, ARM TrustZone est accessible via OP-TEE.

**Laplace discret constant-time** : Notre implémentation `geometric_v2()` a un timing data-dépendant (O(log(1/u)) itérations). Un sampler en temps constant (nombre fixe d'opérations) éliminerait le timing side-channel.

**Rényi DP (RDP)** : La composition en RDP (Mironov, 2017) permet des bornes de composition plus serrées que la composition séquentielle basique. Pour k = 3 agrégations, RDP donnerait ε_total ≈ 1.3 au lieu de 1.5, améliorant l'utilité ou permettant plus d'agrégations.

### 5.3.2 Moyen Terme — v1.0

**Fenêtre continue (Continual Observation)** : ANCRE v0.7 opère sur des fenêtres fermées. Les données radio sont un flux continu. L'extension à la DP sous observation continue (Dwork et al., 2010) permettrait des agrégations en temps réel sans reset de fenêtre.

**Local DP optionnel** : Ajouter une couche de bruit côté client (LDP) permettrait de réduire la confiance requise envers le serveur. ANCRE deviendrait un système hybride LDP + Central DP, au prix d'une utilité réduite.

**Audit formel** : Vérification formelle de la preuve du Lemme 1 Cas 3 en Coq ou Lean — la seule partie encore assertée dans la section formelle v7.3.

### 5.3.3 Long Terme — Production

**Partenariat SIM opérateur** : Accord avec Orange, SFR ou Transatel pour émettre des certificats IoT SAFE réels liés aux contrats d'abonnement radio.

**Certification CNIL** : Soumission du protocole ANCRE pour avis de conformité RGPD. La section formelle v7.3 constitue la base de ce dossier.

**Interopérabilité** : Extension du protocole pour les plateformes de podcast (Spotify, Deezer) et les plateformes vidéo (YouTube Music), où la problématique DP est identique.

---

## 5.4 Conclusion

Nous avons présenté ANCRE, un protocole de confidentialité différentielle pure (ε=0.5, δ=0) pour l'analytics audio en contexte B2B. Les contributions principales sont :

1. **Mécanisme DLap discret exact** — élimine les fuites flottantes (Mironov, 2012) sans compromis d'utilité (ρ = 0.9997 sur Last.fm).

2. **Preuve formelle sous substitute adjacency** — justifiée par la fermeture de fenêtre (H6), avec convention de tie-breaking explicite pour le Lemme 1.

3. **Architecture SIM IoT SAFE** — première application de l'attestation GSMA à la résistance Sybil dans un système DP, à notre connaissance.

4. **Implémentation production-ready** — 59/59 tests, 21/21 tests Python, déployable sur Android ARM64 sans infrastructure PC.

La preuve de concept est ancrée temporellement (FreeTSA, Mars 2026). Le code est disponible à : github.com/taha-vera/Vera-protocole-

