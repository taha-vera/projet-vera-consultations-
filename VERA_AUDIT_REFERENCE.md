# VERA Consultation -- Document de reference pour audit de securite

**Version :** 1.0 -- 09/07/2026
**Depot :** https://github.com/taha-vera/Protocole-Vera
**Contact :** tahahouari@hotmail.fr
**URL production :** https://vera-consultation.duckdns.org

---

## 1. Description du systeme

VERA Consultation est un protocole open source de sondage anonyme pour
organisations (RH, associations, syndicats). Il publie un resultat
collectif bruite sans jamais exposer la contribution individuelle,
et le prouve mathematiquement.

**Flux nominal :**
1. Un compte RH ouvre une consultation et genere N tokens anonymes
2. Chaque participant recoit un token, vote une fois, le token est detruit
3. Les votes sont agreges, bruites par Laplace discret (OpenDP), publies
4. Le compte RH consulte le resultat bruite agrege par departement

**Invariants garantis par le code :**
- La donnee brute n'est jamais stockee ni exposee
- Les sorties sont des agregats statistiques bruites, irreversibles
- Budget epsilon plafonne et borne
- Un token anonyme par individu et par consultation (anti double-reponse)
- Limites documentees, pas dissimulees

---

## 2. Architecture technique

| Composant | Detail |
|---|---|
| Runtime | Python 3.14, FastAPI, uvicorn (1 worker, GIL) |
| Transport | HTTPS (Nginx + Let's Encrypt, vera-consultation.duckdns.org) |
| Persistance | SQLite WAL, write-through, /root/vera_state.db |
| Serveur | Hetzner Cloud, 2 vCPU AMD EPYC, 4GB RAM, Ubuntu 26.04 LTS |
| Supervision | systemd (Restart=on-failure), reboot complet teste |
| DNS | DuckDNS (service tiers gratuit) |
| Certificat | Let's Encrypt, renouvellement automatique Certbot |

**Modules principaux :**
- vera_dp_noise.py -- bruit Laplace discret (OpenDP)
- vera_signature_manager.py -- signature aveugle RSABSSA (RFC 9474)
- vera_persistance.py -- SQLite, chiffrement partiel (cle RSA uniquement)
- vera_epsilon_budget.py -- budget epsilon par population
- vera_consultation_api.py -- API FastAPI

---

## 3. Parametres de confidentialite differentielle

| Parametre | Valeur | Justification |
|---|---|---|
| Mecanisme | Laplace discret (OpenDP) | Bibliotheque auditee, garantie analytique |
| Delta | 2 | Vote binaire, adjacence par substitution (bounded DP) |
| Scale | 4 | epsilon = Delta/scale = 0.5 exact |
| epsilon par publication | 0.5 | Calcule analytiquement par meas.map() |
| Bounds | (0, 10000) | Plafond effectif d'un departement |
| Budget total | epsilon_total = 1.5 | Max 3 publications par population |
| Indexation budget | Par departement (population), pas par question | Composition sequentielle globale |
| K_MIN | 100 | Sous ce seuil, resultat publie mais signale non fiable cote client |

**Verifications empiriques :**
- AUC MIA = 0.6209 (test 50 vs 52, Delta=2, N=100000, IC95%=[0.6185,0.6232])
- Borne theorique pire cas : 0.6225 -- AUC dans IC confirme (True)
- Canal temporel : Spearman p=0.38, Mann-Whitney p=0.11 sur vera_dp_noise.py
- Budget robuste sous 10 requetes concurrentes (verrou threading.Lock)

---

## 4. Cryptographie

| Element | Detail |
|---|---|
| Signature aveugle | RSABSSA-SHA384-PSS-Randomized (RFC 9474), module Rust/PyO3 |
| Rotation cle RSA | Par consultation (48h), threading.Timer |
| Persistance cle privee | Fernet/AES-128 + PBKDF2-SHA256 (100 000 iterations, salt aleatoire 16 bytes, os.urandom) |
| Secret de derivation | VERA_DB_KEY (variable d'environnement systemd, permissions 600) |
| Anti-rejeu | Empreinte SHA-256 du token + horodatage_unix (precis a la seconde, NON chiffre) |
| Transport | TLS via Nginx + Let's Encrypt, redirection HTTP->HTTPS 301 |
| Fail-closed | Si vera_blind_sig ne charge pas : RuntimeError, refus de demarrer |
| Anti-bruteforce | /api/resoudre_code : 5 echecs max par IP, blocage 5 minutes. Protection en memoire (perdue au redemarrage -- limite assumee) |


---

## 5. Modele de menace -- 17 portes

| # | Vecteur | Statut | Preuve / Note |
|---|---|---|---|
| 1 | Mecanisme de bruit | Fermee | OpenDP, Delta=2, scale=4, epsilon=0.5 exact |
| 2 | MIA generale | Fermee | AUC=0.6279, TPR@1%FPR=1.65% |
| 3 | Canal temporel | Fermee* | Fuite sub-microseconde (0.209us), inexploitable via reseau HTTP |
| 4 | Composition sequentielle | Fermee | Budget par population, robuste sous 10 requetes concurrentes |
| 5 | Observateur reseau | Assumee | Hors-perimetre, delegue VPN/Tor |
| 6 | Coercition | Assumee | Limite partagee par tout systeme de vote |
| 7 | Differentiation 49/1 | Fermee | RSABSSA RFC 9474, fail-closed teste dans les deux sens |
| 8 | Inference outlier | Fermee | AUC=0.6279, TPR@1%FPR=1.65% |
| 9 | Collusion emetteur/agregateur | Fermee | Secret admin distinct, isolation testee |
| 10 | Sondage binaire K_MIN | Fermee | Champs effectif/fiable retires de l API |
| 11 | Acces SQLite / cle RSA | Fermee | Fernet/AES-128, salt PBKDF2 aleatoire, crash-teste + reboot complet |
| 12 | Secret admin visible /proc | Assumee | Solo-root : acces root couvre deja Porte 11 |
| 13 | Soustraction d agregats | Assumee | Limite irreductible DP, attenuee par budget epsilon=1.5 |
| 14 | Non-persistance de l etat | Fermee | SQLite WAL, teste crash process ET reboot systeme complet |
| 15 | Trafic HTTP en clair | Fermee | HTTPS Nginx + Let Encrypt, redirection 301 verifiee |
| 16 | Retention logs applicatifs | Fermee | Purge manuelle a cloture + logrotate 3 jours |
| 17 | Correlation temporelle horodatage_unix | Assumee | Table anti-rejeu non chiffree, protection reelle via K_MIN=100 |

Resume : 11 portes fermees avec preuve empirique datee, 4 limites assumees avec justification, 2 hors-perimetre documentes.

---

## 6. Infrastructure et operations

| Aspect | Etat |
|---|---|
| DNS | DuckDNS (service tiers gratuit) -- dependance non redondee |
| Certificat TLS | Let Encrypt, renouvellement automatique Certbot |
| Supervision | systemd Restart=on-failure, teste kill -9 et reboot complet |
| Logs | IP source + chemin + code retour uniquement. Purge manuelle + logrotate 3 jours |
| Base SQLite | Seule la cle RSA est chiffree. Budget epsilon, compteurs, horodatages en clair |
| Backup | Aucun backup automatique de vera_state.db |
| Compte execution | root (serveur dedie solo) |
| Scalabilite | 1 worker uvicorn, ~45 req/s stable, ~800 000 participants sur 24-48h |

---

## 7. Limites explicitement hors-perimetre

- L1 Observateur reseau (IP, timing en transit) -- delegue VPN/Tor
- L2 Coercition physique ou sociale
- L3 Tres petits groupes sous K_MIN=100 -- resultat publie mais signale non fiable
- L4 Qualification juridique CNIL/DPO (anonymisation vs pseudonymisation, art. 5(1)(e) RGPD) -- avis externe requis

---

## 8. Ce que ce document ne prouve pas

- Que le code est exempt de bugs non identifies
- Que les limites assumees sont negligeables dans tous les contextes
- Que la qualification CNIL est acquise (L4)
- Que le service tiers DuckDNS est fiable a 100%
- Qu un expert humain en cryptographie ne trouverait rien de nouveau

Ce document reflète l etat verifie au 09/07/2026. Toute nouvelle porte
identifiee est documentee dans VERA_THREAT_MODEL_COMPLETE.md avec sa date
et sa preuve.
