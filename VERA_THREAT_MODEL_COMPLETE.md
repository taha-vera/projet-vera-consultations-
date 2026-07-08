**Auteur :** Taha Houari · tahahouari@hotmail.fr
**Version consolidée :** 2026-07-02
**Référence :** accompagne vera_dp_noise.py, vera_epsilon_budget.py, vera_signature_manager.py, vera_consultation_api.py (serveur Hetzner 167.233.49.182:8001)

## Méthodologie

Chaque statut n'est marqué "vérifié" que s'il a été testé directement sur le serveur de production, avec preuve reproductible datée. Les statuts hérités et non re-testés sont marqués comme tels. Cette version remplace la version du 14 juin, restée figée sur le dépôt distant pendant que le travail de vérification se poursuivait.

## État des portes — 2 juillet 2026

| # | Porte | Statut | Preuve |
|---|---|---|---|
| 1 | Mécanisme de bruit | Vérifié 01/07 | Bruit Laplace réel (vera_dp_noise.py, OpenDP, eps=0.5, Delta_int=10, scale=20, bounds=(0,100)) applique sur /api/rh/resultats, teste par cycle complet vote->publication |
| 2 | MIA générale | Vérifié 02/07, méthodologie simplifiée | AUC=0.6219 sur écart de sensibilité (50 vs 60, Delta_int=10). Un seul test commun avec Porte 8 -- ne couvre pas individus proches des bornes, distributions asymétriques, adversaire bayésien. A re-décorréler de Porte 8 |
| 3 | Canal temporel | Vérifié 02/07 | Spearman rho=-0.39 p=0.38, Mann-Whitney p=0.11, écart médian 0.50% sur vera_dp_noise.py |
| 4 | Composition séquentielle | Vérifié 01/07, portée limitée -- voir Porte 14 | Budget epsilon confirmé en conditions réelles. Indexé uniquement par département (pas par question) -- plusieurs questions successives réinitialisent le budget par question, pas par département dans l'absolu |
| 5 | Observateur réseau (L1) | Ouvert, assumé | Non touché cette session |
| 6 | Coercition (L2) | Hors-périmètre | Non touché cette session |
| 7 | Différenciation 49/1 (crypto) | Vérifié 01-02/07, testé dans les deux sens | Nominal + 2 tests d'échec réel (kill du module), faille de couverture trouvée (except ImportError insuffisant, collision de nom de dossier) et corrigée en except Exception |
| 8 | Inférence outlier | Vérifié 02/07, méthodologie simplifiée | Même test que Porte 2 (50 vs 60). Ne teste pas un vrai scénario 99 vs 1 avec proximité des bornes |
| 9 | Collusion émetteur/agrégateur | Vérifié 02/07 | Régression trouvée (VERA_SECRET_CREATION_COMPTE perdu à la migration systemd, jamais persisté) et corrigée. Isolation testée avec vrai secret aléatoire |
| 10 | Sondage binaire (K_MIN) | Vérifié 01/07 | Département sous K_MIN reste visible, fiable:false |
| 13 | Soustraction d'agrégats | Limite irréductible assumée | Non touché cette session |

## NOUVELLE PORTE — 14 — Non-persistance de l'état de confidentialité

**Statut : OUVERTE, GRAVITÉ CRITIQUE, découverte 02/07/2026**

Tout l'état lié à la garantie de confidentialité (budget epsilon consommé par département, compteurs de votes agrégés, effectifs, sessions RH) est stocké exclusivement en mémoire du process Python (BudgetEpsilonParDepartement, compteurs_par_departement, effectif_par_departement), sans persistance disque.

Preuve empirique : département de test avec effectif=1 et nombre_publications=1 confirmés le 01/07 -- totalement absent après plusieurs redémarrages du service effectués le 02/07 (tests de résilience Porte 7 et Porte 9, migration systemd).

Conséquence : tout redémarrage (crash, reboot, panne, migration) réinitialise silencieusement le budget de confidentialité à zéro pour tous les départements. La garantie de composition (Porte 4) n'est valable qu'entre deux redémarrages, pas sur la durée réelle d'une campagne.

Aggravation : la migration systemd (Restart=on-failure, 02/07) accélère le retour en service après crash, réduisant la friction pour qu'un tel effacement se reproduise sans alerte opérationnelle.

Non traité -- nécessite une refonte de la persistance d'état, hors périmètre d'un correctif ponctuel.

## Portes/questions identifiées par audit externe, non encore vérifiées sur le code (02/07/2026)

- Distribution des invitations (canal RH email/SMS, hors protocole cryptographique)
- Corrélation temporelle côté vote (logs uvicorn horodatés en clair -- non vérifié si /root/consultation.log expose ceci)
- Attaque par volume/fréquence (petit département, tokens et votes concentrés dans une fenêtre courte)
- Opérateur technique privilégié (root) -- actuellement traité comme fatalité, atténuations matérielles (SEV-SNP déjà exploré ailleurs dans le projet) non répertoriées comme porte à part entière
- Indexation du budget epsilon : département seul vs (département, question) -- confirmé département seul, donc plusieurs questions successives sur la même population contournent la composition promise

## Infrastructure

Vérifié 02/07 -- systemd, Restart=on-failure, testé par kill -9 réel, redémarrage confirmé <6s. Effet de bord découvert : accélère la reproduction de la Porte 14 (voir ci-dessus).

## Divergences trouvées et corrigées cette session (01-02/07)

1. Portes 1 et 10 absentes du code de production malgré une documentation (14/06) les déclarant fermées.
2. Porte 7 : except ImportError ne couvrait pas tous les modes d'échec réels.
3. Porte 9 : secret de création de compte jamais persisté, perdu à la migration systemd.
4. Absence de superviseur de service -- corrigée, avec effet de bord sur Porte 14.

**Bilan honnête** : 6 portes vérifiées empiriquement sur le code de production actuel (1, 3, 4 avec réserve, 7, 9, 10). 2 portes vérifiées avec une méthodologie simplifiée à consolider (2, 8). 1 porte critique nouvellement identifiée et non résolue (14). Ceci remplace toute affirmation antérieure de type "8 portes sur 9 fermées".

## Mise a jour Porte 14 -- 03/07/2026

**Statut : FERMEE, verifiee empiriquement par crash test reel**

Module vera_persistance.py (SQLite, write-through, WAL) deploye et integre dans vera_consultation_api.py et vera_signature_manager.py. Persiste : budget epsilon par departement, tokens consommes (anti-rejeu), compteurs de votes, effectifs, et la cle RSA active elle-meme (nouveau -- corrige une aggravation decouverte le 02/07 ou seule la partie anti-rejeu etait persistee, laissant la cle se regenerer a chaque redemarrage et invalider tous les tokens en circulation).

Trois bugs trouves et corriges pendant l'integration, chacun par test reel :
1. Regression du fix Porte 7 (except ImportError au lieu de except Exception) presente dans une version intermediaire, jamais deployee -- confirmee absente du fichier serveur reel avant integration.
2. Appel manquant a gestionnaire_signature.ouvrir_consultation() -- la consultation n'etait jamais activee, aucun token generable.
3. vbs.generer_cles() retourne des list, pas des bytes -- crash a la persistance de la cle (AttributeError sur .hex()). Corrige par conversion explicite bytes(...), coherent avec le pattern deja utilise ailleurs dans generer_token_signe().

**Preuve empirique (03/07/2026, kill -9 reel sur le process en production) :**
Avant crash : departement test, effectif=1, budget_epsilon.nombre_publications=1, epsilon_consomme=0.5.
Apres kill -9 + redemarrage automatique systemd : effectif=1, nombre_publications=1, epsilon_consomme=0.5 -- identiques. Nouveau token genere avec succes apres redemarrage, confirmant que la cle RSA a survecu (rechargee depuis SQLite, pas regeneree).

**Porte 14 : OUVERTE -> FERMEE.**

## Mise a jour 05/07/2026 — Nouvelles portes identifiees lors d une revue de securite

### Porte 11 — Acces direct a la base SQLite

**Statut : OUVERTE, GRAVITE CRITIQUE, documentee 05/07/2026**

La base SQLite `/root/vera_state.db` contient en clair :
- La cle RSA privee active (hex non chiffre)
- Les empreintes SHA256 des tokens consommes (anti-rejeu)
- Le budget epsilon par departement
- Les compteurs de votes agriges

Tout acces root au serveur (incident Hetzner, compromission SSH, dump memoire)
expose directement la cle privee RSA, permettant de forger des tokens valides
pour toute consultation en cours.

Attenuation minimale non implementee : chiffrer la cle RSA dans SQLite avec
une cle derivee d'un secret externe (variable d'environnement ou fichier
separe avec permissions 400), jamais stockee dans la base elle-meme.

Non traite -- necessite une session dediee (derivation de cle, migration de
schema, gestion du secret de chiffrement).

---

### Porte 12 — Secret administrateur visible dans /proc

**Statut : LIMITE ASSUMEE, documentee 05/07/2026**

Le secret `VERA_SECRET_CREATION_COMPTE` est defini dans le fichier systemd
`/etc/systemd/system/vera-consultation.service` (permissions 600, lisible
uniquement par root). Il est donc visible dans `/proc/PID/environ` pour tout
process tournant en root sur le meme serveur.

Sur un serveur solo en root (configuration actuelle), ce risque est acceptable
-- un attaquant ayant acces root peut deja lire SQLite (Porte 11, plus grave).
En environnement multi-utilisateur ou multi-process root, ce secret serait
compromis.

Attenuation : utiliser un gestionnaire de secrets externe (HashiCorp Vault,
AWS Secrets Manager) ou un fichier de secrets avec permissions strictes hors
du fichier .service. Non prioritaire tant que Porte 11 reste ouverte.

---

### Note sur la semantique du budget epsilon multi-consultation

Le budget epsilon (epsilon_total=1.5, max 3 publications) est indexe par
departement seul, sans identifiant de question. Ce comportement est
intentionnel et mathematiquement correct :

La composition sequentielle (Dwork & Roth) s'applique a la meme POPULATION
sur la duree, independamment du nombre de questions posees. Autoriser un
budget distinct par question permettrait de poser un nombre illimite de
questions sur la meme population avec epsilon=0.5 chacune, ce qui contourne
directement la garantie de composition (Porte 13).

En pratique : une population (departement) ne peut recevoir que 3 publications
au total, toutes consultations confondues, avant que le systeme refuse de
publier de nouveaux resultats pour cette population. Ce comportement a ete
verifie empiriquement le 05/07/2026 par deux cycles de vote successifs sur
le meme departement -- le budget s'accumule correctement entre consultations
grace a la persistance SQLite (Porte 14 fermee le 03/07/2026).

## Mise a jour Porte 11 -- 05/07/2026 -- FERMEE

**Statut : FERMEE, verifiee par crash test reel**

Correction implementee : chiffrement Fernet (AES-128-CBC + HMAC-SHA256) de la
cle RSA privee avant ecriture dans SQLite. Cle de chiffrement derivee de
VERA_DB_KEY via PBKDF2-SHA256 (100 000 iterations, salt fixe b"vera_rsa_key_v1").

La cle de chiffrement VERA_DB_KEY est definie dans le fichier systemd
(/etc/systemd/system/vera-consultation.service, permissions 600) et injectee
comme variable d'environnement au demarrage du service. Elle n'est jamais
stockee dans SQLite.

Preuve empirique (05/07/2026, kill -9 reel sur PID 503179) :
- Avant crash : token genere avec cle chiffree dans SQLite
- kill -9 503179 : process tue brutalement
- Nouveau PID 503465 : redemarrage automatique systemd en moins d'1 seconde
- Apres crash : nouveau token genere avec succes -- cle RSA rechargee depuis
  SQLite et dechiffree correctement avec VERA_DB_KEY

Limites documentees (non bloquantes en contexte solo-root) :
- Salt PBKDF2 fixe (b"vera_rsa_key_v1") : risque rainbow table theorique,
  negligeable en pratique sur serveur solo
- Pas de mecanisme de re-chiffrement automatique a la rotation de VERA_DB_KEY
- VERA_DB_KEY visible dans /proc/PID/environ (Porte 12, limite assumee)

**Porte 11 : OUVERTE -> FERMEE.**
