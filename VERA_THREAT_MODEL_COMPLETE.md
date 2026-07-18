**Auteur :** Taha Houari · tahahouari@hotmail.fr
**Version consolidée :** 2026-07-02
**Référence :** accompagne vera_dp_noise.py, vera_epsilon_budget.py, vera_signature_manager.py, vera_consultation_api.py (serveur Hetzner 167.233.49.182:8001)

## Méthodologie

Chaque statut n'est marqué "vérifié" que s'il a été testé directement sur le serveur de production, avec preuve reproductible datée. Les statuts hérités et non re-testés sont marqués comme tels. Cette version remplace la version du 14 juin, restée figée sur le dépôt distant pendant que le travail de vérification se poursuivait.

## État des portes — 2 juillet 2026

| # | Porte | Statut | Preuve (a jour 16/07/2026) |
|---|---|---|---|
| 1 | Mécanisme de bruit | Fermée | Laplace vectoriel OpenDP (Laplace discret), Delta_1=2, scale=4, eps=0.5, bounds=(0,10000). Projection sur le simplexe par clip-and-shift iteratif (post-traitement inspire de Hay et al. 2010 ; heuristique de coherence, pas la projection L2 exacte de Duchi ; gain ~25% mesure empiriquement). Verifie par test_precision_kmin.py |
| 2 | MIA générale | Fermée | AUC=0.6209, IC95% [0.6185, 0.6232], borne theorique 0.6225 incluse (N=100000, bootstrap) |
| 3 | Canal temporel | Fermée | Fuite sub-microseconde. Test etendu 7 valeurs N=10000 : Spearman rho=-0.14 p=0.76, pas de correlation valeur/temps. Inexploitable via reseau (latence 50-100ms) |
| 4 | Composition séquentielle | Fermée | Budget eps=0.5 par population = UNE publication (resultat fige a la premiere, republier renvoie le meme resultat -> pas de moyennage) |
| 5 | Observateur réseau (L1) | Limite assumée | Hors-perimetre (VPN/Tor au choix de l'utilisateur) |
| 6 | Coercition (L2) | Limite assumée | Hors-perimetre, partagee par tout systeme de vote |
| 7 | Différenciation 49/1 (crypto) | Fermée | Primitive de production : signature aveugle RSABSSA RFC 9474 (vera_signature_manager.py, standard audite). La LOGIQUE de partition (nominal, double-depense, 49/1 bloquee, rejeu cross-epoque) est validee 9/9 sur un prototype (archive/test_porte7.py) ; ce prototype n est PAS la primitive de production. Primitive de prod testee par test_signature_production.py (6/6, memoire pure isolee) : flux nominal, anti-rejeu, token force rejete, malforme sans crash, round-trip URL, et token d une AUTRE cle rejete (preuve que la signature est verifiee, pas juste decodee). | | NOTE 18/07 : unlinkability du votant NON effective -- le serveur genere le token complet (aveuglement+finalisation cote serveur). Contenu protege, mais non-liaison identite<->vote a corriger (crypto cote client, chantier dedie).
| 8 | Inférence outlier | Fermée | AUC=0.6209 (meme mesure que Porte 2). Composition : fuite k=1 garantie par la partition (Porte 7), TPR@1%FPR=1.6% |
| 9 | Collusion émetteur/agrégateur | Fermée | Secret admin distinct, comptes separes, isolation testee avec secret aleatoire |
| 10 | Sondage binaire (K_MIN) | Fermée | REFUS de publier sous K_MIN=240 (aucun resultat, pas de version degradee). Champs effectif/fiable retires. Effectif exact des petites cohortes non expose |
| 11 | Accès direct SQLite / clé RSA | Fermée | Chiffrement Fernet/AES-128, sel PBKDF2 aleatoire, crash-testee |
| 12 | Secret admin visible /proc | Limite assumée | Contexte solo-root |
| 13 | Soustraction d'agrégats | Limite assumée | Limite irreductible DP, attenuee par publication unique (eps=0.5, resultat fige) |

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

**Statut initial (05/07/2026 matin) : OUVERTE, GRAVITE CRITIQUE.**
**Statut final (05/07/2026 soir) : FERMEE — voir section "Mise a jour Porte 11" plus bas pour la correction et la preuve empirique.**

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
du fichier .service. Porte 11 est desormais fermee (voir plus bas) ; Porte 12 reste une limite assumee independamment.

---

### Note sur la semantique du budget epsilon multi-consultation

Le budget epsilon (epsilon_total=0.5, UNE publication par population) est indexe par
departement seul, sans identifiant de question. Ce comportement est
intentionnel et mathematiquement correct :

La composition sequentielle (Dwork & Roth) s'applique a la meme POPULATION
sur la duree, independamment du nombre de questions posees. Autoriser un
budget distinct par question permettrait de poser un nombre illimite de
questions sur la meme population avec epsilon=0.5 chacune, ce qui contourne
directement la garantie de composition (Porte 13).

En pratique : une population (departement) ne recoit qu'UNE publication (le resultat bruite est fige a la premiere publication, republier renverrait le meme resultat -- ce qui empeche le moyennage du bruit). L'ancienne mention de "3 publications" etait de la logique morte : le code figeait deja le resultat des la premiere.
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

Limites documentees a l origine (non bloquantes en contexte solo-root) :
- Salt PBKDF2 fixe (b"vera_rsa_key_v1") : risque rainbow table theorique,
  negligeable en pratique sur serveur solo -- CORRIGE le 05/07/2026 (soir) :
  salt aleatoire de 16 bytes (os.urandom) genere et persiste par
  enregistrement, teste par cycle complet + crash test reel
- Pas de mecanisme de re-chiffrement automatique a la rotation de VERA_DB_KEY
  -- non corrige, limite toujours actuelle
- VERA_DB_KEY visible dans /proc/PID/environ (Porte 12, limite assumee)
  -- non corrige, limite assumee toujours actuelle

**Porte 11 : OUVERTE -> FERMEE.**

## Nouvelle porte -- 09/07/2026

### Porte 15 -- Trafic en clair (HTTP, absence de TLS)

**Statut : FERMEE, verifiee empiriquement 09/07/2026**

Jusqu'au 09/07/2026, tout le trafic entre client et serveur transitait en
HTTP non chiffre (http://167.233.49.182:8001). Consequence : mots de passe
RH, cookies de session, et tokens de vote signes transitaient en clair sur
le reseau, interceptables par toute personne en position d'observer le
trafic (WiFi public, FAI, noeud intermediaire).

Correction : reverse proxy Nginx + certificat Let's Encrypt (Certbot) sur
un sous-domaine DuckDNS (vera-consultation.duckdns.org, gratuit, pas de
domaine propre necessaire). Redirection automatique HTTP -> HTTPS (301)
configuree par Certbot.

Preuve empirique (09/07/2026) :
- curl https://vera-consultation.duckdns.org/api/health : reponse normale,
  trafic chiffre confirme
- curl -I http://vera-consultation.duckdns.org/api/health : 301 Moved
  Permanently vers https://, aucun acces HTTP direct possible
- Cycle complet connexion RH teste avec succes via HTTPS (cookie de
  session emis correctement)

Certificat valide jusqu'au 07/10/2026, renouvellement automatique
programme par Certbot (systemd timer).

**Porte 15 : OUVERTE -> FERMEE.**

## Verification complementaire -- 09/07/2026

### Robustesse du budget epsilon sous charge concurrente

Teste : 10 requetes simultanees (bash, execution parallele via &) sur
/api/rh/resultats, portant sur 5 departements distincts deja publies une
fois chacun.

Resultat : nombre_publications=1 et epsilon_consomme=0.5 identiques sur
les 10 reponses, pour chacun des 5 departements -- aucune consommation
multiple du budget detectee malgre la charge concurrente. Le verrou
(threading.Lock, logique deja_publie) protege correctement.

Aucune nouvelle porte identifiee par ce test -- confirme la robustesse
du mecanisme de Porte 4 (composition sequentielle) sous concurrence.

## Verification complementaire -- 09/07/2026

### Robustesse du budget epsilon sous charge concurrente

Teste : 10 requetes simultanees (bash, execution parallele via &) sur
/api/rh/resultats, portant sur 5 departements distincts deja publies une
fois chacun.

Resultat : nombre_publications=1 et epsilon_consomme=0.5 identiques sur
les 10 reponses, pour chacun des 5 departements -- aucune consommation
multiple du budget detectee malgre la charge concurrente. Le verrou
(threading.Lock, logique deja_publie) protege correctement.

Aucune nouvelle porte identifiee par ce test -- confirme la robustesse
du mecanisme de Porte 4 (composition sequentielle) sous concurrence.

## Nouvelle porte -- 09/07/2026

### Porte 16 -- Retention des logs applicatifs

**Statut : FERMEE, verifiee empiriquement 09/07/2026**

Le fichier /root/consultation.log (sortie uvicorn) journalise chaque requete
HTTP avec adresse IP source, chemin d'URL, et code de retour -- pas les
tokens ni mots de passe (verifie par grep, aucune occurrence trouvee). Sans
politique de retention, ce fichier grossissait indefiniment et conservait
des adresses IP sans limite de duree, potentiellement exploitables pour de
la correlation temporelle si un acces au fichier etait obtenu.

Correction, deux mecanismes complementaires :
1. Script /root/purger_logs_apres_publication.sh -- purge manuelle du log
   applicatif, a executer par l'operateur une fois une consultation cloturee
   et ses resultats diffuses. Coherent avec le principe de non-persistance
   applique au reste du systeme.
2. logrotate (/etc/logrotate.d/vera-consultation) -- filet de securite
   automatique, rotation quotidienne, retention 3 jours, compression.
   Verifie actif via logrotate.timer (systemd, prochaine execution
   confirmee).

Preuve empirique (09/07/2026) :
- grep sur le contenu du log : aucun token, mot de passe, ou header
  sensible trouve
- logrotate -d (dry run) : configuration validee sans erreur
- systemctl status logrotate.timer : actif, enabled, prochaine execution
  planifiee

**Porte 16 : OUVERTE -> FERMEE.**

## Renforcement de preuve -- Porte 14 -- 09/07/2026

**Test complementaire : reboot systeme complet (pas seulement crash de process)**

Le test du 03/07/2026 validait la survie de l'etat via kill -9 (crash du
process uvicorn, redemarrage automatique par systemd Restart=on-failure).
Ce test etait insuffisant pour couvrir un vrai reboot serveur (arret complet
du systeme, reinitialisation reseau, ordre de demarrage des services).

Test effectue (09/07/2026) : systemctl reboot reel sur le serveur de
production, avec mise a jour noyau (7.0.0-15 -> 7.0.0-27) au passage.

Resultat :
- vera-consultation.service et nginx.service redemarres automatiquement
  au boot (systemctl status confirme active/running, PID differents,
  aucune intervention manuelle)
- Healthcheck HTTPS repond normalement apres reboot
- 5 departements de test verifies : nombre_publications=1 et
  epsilon_consomme=0.5 identiques avant et apres le reboot complet

Porte 14 dispose desormais d'une preuve couvrant a la fois le crash de
process (03/07) et le reboot systeme complet (09/07) -- niveau de
confiance renforce sur la persistance reelle en conditions de production.

## Nouvelle porte -- 09/07/2026

### Porte 17 -- Correlation temporelle via horodatage_unix (anti-rejeu SQLite)

**Statut : LIMITE ASSUMEE, documentee 09/07/2026**

La table tokens_consommes (introduite par Porte 14, persistance SQLite)
stocke un timestamp precis a la seconde (horodatage_unix) pour chaque token
consomme. Verifie empiriquement le 09/07/2026 -- les timestamps sont bien
precis a la seconde pres (ex: 1783120902.54973).

Risque : un attaquant avec acces a cette table, combine a une connaissance
externe de l'heure d'envoi d'un lien de vote a une personne precise (ex.
surveillance de la messagerie du RH, connaissance de l'heure d'une reunion
de distribution), pourrait recouper les deux pour desanonymiser un vote
dans un petit groupe.

Note : contrairement a la cle RSA (Porte 11), cette table n'est pas
chiffree -- seule la cle RSA beneficie du chiffrement Fernet/AES-128.

Options evaluees et raisons du choix :
- Reduire la precision du timestamp (heure ou jour pres) : rejete, casse
  la capacite de diagnostic technique sans reellement empecher la
  correlation si l'attaquant a acces a d'autres sources de timing
  (logs HTTP, timing reseau).
- Chiffrer la table : rejete, un attaquant disposant deja de VERA_DB_KEY
  (necessaire pour dechiffrer la cle RSA) pourrait dechiffrer cette table
  aussi -- protection illusoire si l'attaquant a deja acces complet.
- Limite assumee (choix retenu) : la vraie protection contre la
  correlation temporelle vient de la taille du groupe (K_MIN=100), pas
  du masquage du timestamp lui-meme. Un attaquant capable d'exploiter
  cette porte a deja un acces root complet au serveur (meme prerequis
  que Porte 11), ce qui rend la question largement redondante avec les
  limites deja assumees en contexte solo-root (Porte 12).

Attenuation partielle deja en place : la separation des roles (RH ne
connait que departement <-> quantite de tokens, jamais l'identite
individuelle des votants cote serveur, cf. ATTRIBUTION_FLOW.md) limite
la capacite du RH lui-meme a exploiter cette correlation, meme s'il a
acces aux logs de sa propre messagerie d'envoi.



Extension -- attaque par volume/frequence : le meme horodatage_unix permet
aussi de detecter qu'un groupe de tokens consommes dans une fenetre courte
(ex. 3 tokens generes, 3 votes en moins d'une minute) revele une forte
participation quasi-simultanee, meme sans connaitre le contenu des votes.
Meme statut, meme justification que ci-dessus : protection reelle via
K_MIN=100, pas via masquage du timing.

**Porte 17 : identifiee et assumee, pas de correction technique prevue.**


## Renforcement de preuve -- Porte 2 -- 12/07/2026

Suite au challenge Mistral (Tour 1) qui pointait que AUC=0.6279 > borne
theorique 0.6225, re-mesure avec N=100000 et bootstrap 1000 iterations :

AUC = 0.6209 (sous la borne theorique)
IC 95% : [0.6185, 0.6232]
Borne theorique 0.6225 dans IC : True

L'AUC precedente (0.6279 sur N=20000) etait un artefact de variabilite
statistique du a un echantillon insuffisant. La garantie DP est confirmee
avec un niveau de confiance plus eleve. Porte 2 reste FERMEE.

## Audit Fable 5 sur code reel -- 13/07/2026 -- 4 vrais bugs corriges

Fable 5 est la seule IA du Tour 1 a avoir lu le CODE reel (pas seulement
la description). Elle a trouve 4 vrais bugs, dont un critique invalidant
la garantie DP. Tous corriges et verifies empiriquement le 13/07/2026.

### BUG CRITIQUE -- Porte 1/2 : bruit DP re-tire a chaque appel

Avant correction : /api/rh/resultats re-tirait un nouveau bruit Laplace a
CHAQUE appel, y compris apres la premiere publication (le compteur de
budget restait a 1, ce qui masquait le probleme). Un compte RH pouvait
appeler N fois, obtenir N tirages bruites independants de la meme valeur,
et les moyenner -- le bruit s'annule, epsilon reel -> infini. La garantie
DP etait cassee des la 2e lecture.

Le test de concurrence precedent (10 requetes -> publications=1) ne
detectait pas ce bug car il verifiait le compteur, pas la variance du
bruit renvoye.

Correction : le resultat bruite est calcule UNE SEULE FOIS a la premiere
publication, persiste dans une nouvelle table SQLite resultats_publies,
et renvoye fige a tous les appels suivants. Verifie : 5 appels successifs
renvoient un resultat identique (bruit fige, moyennage impossible).

### BUG eleve -- endpoints /api/test/* en production

/api/test/verifier_token_signe appelait verifier_et_consommer(), brulant
un vrai token (ajout a l'anti-rejeu). Exploitable en DoS : bruler les
tokens des participants avant qu'ils votent. Corrige : endpoints supprimes
de la production (404 confirme).

### BUG eleve -- schema salt_hex manquant (deploiement from scratch)

La table cle_rsa_active etait creee sans colonne salt_hex dans le CREATE
TABLE, alors que persister_cle_rsa_chiffree fait un INSERT avec salt_hex.
Fonctionnait sur le serveur actuel (ALTER TABLE manuel de juillet) mais
un deploiement propre from scratch aurait plante. Corrige : salt_hex
ajoute au schema.

### BUG moyen -- anti-bruteforce voyait 127.0.0.1

Derriere Nginx, request.client.host valait 127.0.0.1 pour tous les
clients. L'anti-bruteforce de /api/resoudre_code etait donc soit global
(tout le monde bloque apres 5 echecs cumules), soit inefficace. Corrige :
lecture de X-Real-IP / X-Forwarded-For. Verifie : 5x404 puis 429.

**Lecon : une porte "Fermee" sur description n'est pas fermee sur code.
Seul l'audit du code reel a revele ces 4 bugs. Les 4 autres IA, auditant
la description, avaient valide un systeme qui contenait un bug critique.**


## Renforcement Porte 14 -- 17/07/2026 -- Effacement actif (cloture)

La non-persistance passive (l'etat ne survit pas a un crash) est desormais
completee par un effacement ACTIF et verifiable : l'endpoint
POST /api/rh/cloturer efface l'integralite de l'etat brut de la consultation
(compteurs_votes, effectifs, codes_courts, tokens_consommes, budget_epsilon,
resultats_publies) en une transaction, detruit la cle de signature, puis
rouvre une consultation neuve.

Difference avec la non-persistance seule : la Porte 14 garantissait qu'un
crash ne laisse pas d'etat exploitable en memoire ; la cloture garantit que
meme la base SQLite ne contient plus rien apres l'operation. L'organisateur
peut donc PROUVER la minimisation (RGPD art. 5(1)(e)) : avant cloture N
departements, apres cloture 0. Teste en conditions reelles (10 -> 0).

Fonction de persistance : effacer_etat_consultation() dans vera_persistance.py
(ne touche PAS a la cle RSA d'infrastructure -- seulement l'etat de la
consultation). Endpoint authentifie RH, action irreversible avec double
confirmation cote interface.