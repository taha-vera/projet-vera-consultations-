# Procédure de reprise — VERA Consultation

À conserver **avec** la copie de `VERA_DB_KEY` (enveloppe scellée), pas séparément.
Ce document ne contient aucun secret : les valeurs à coller viennent de
l'enveloppe, jamais d'ici.

Écrit pour quelqu'un qui n'a jamais touché le projet. Chaque commande peut être
copiée-collée telle quelle, sauf les lignes marquées `<<< À REMPLACER >>>`.

**Version 2** — corrigée après un audit ciblé du 21/09/2026 qui a trouvé la
version précédente inutilisable telle quelle en cas B (chemins qui ne
correspondaient pas à l'unité réelle), et plusieurs imprécisions en cas A
(diagnostic qui regardait le mauvais endroit). Détail des corrections en fin
de document.

**Version 3** (22/09/2026) — ajoute la restauration depuis une sauvegarde
chiffrée (`sauvegarder_base.sh`), qui n'existait pas en version 2.

**Version 4** (22/09/2026) — la version 3 du script (auto-numérotée
« VERSION 1 » dans son propre en-tête — cette numérotation-là est interne au
script, distincte des numéros de version de ce document) sauvegardait toute
la base chaque nuit. Un audit ciblé, vérifié sur un clone frais, a montré que
ça rétablissait, à l'échelle du jour, la fuite que le projet a fermée en
abandonnant `journal_mode=WAL` le 13/08/2026 : deux instantanés consécutifs
de la base, lus ensemble, réassignent un vote à un votant via le jeton
(donc l'identité, par la liste tenue par l'organisation). Réduire à une seule
sauvegarde ne suffisait pas non plus — vérifié aussi — puisque la base
vivante et cette unique sauvegarde forment déjà la même paire comparable, en
une seule lecture de `/root`.

**Depuis cette version, le script (« VERSION 2 » dans son propre en-tête)
n'exporte plus qu'une seule table : `historique_consultations`** (quel
groupe a clôturé, et quand). Jamais de compteur, de jeton, de clé, ni la
table `question_active`. Rien dans cette sauvegarde ne peut être relié à un
votant. **Conséquence assumée : une consultation en cours n'est plus
récupérable depuis cette sauvegarde en cas de perte du serveur** — elle est
perdue et relancée avec de nouveaux liens, le même arbitrage que celui du
13/08 (accepter 632 votes/s au lieu de 1450 pour fermer ce canal), appliqué
à la sauvegarde plutôt qu'au mode de journalisation. La Partie 3 ci-dessous a
changé en conséquence.

**Version 5** (23/09/2026) — un audit ciblé sur ce document lui-même,
vérifié sur un clone frais, a trouvé sept défauts, dont deux bloquants ou
sérieux en pratique : les chemins Python de la Partie 3 et du cron
supposaient l'agencement de l'*ancien* serveur au lieu de celui que la
Partie 2 crée réellement (la Partie 3 échouait silencieusement, et le cron
d'un serveur neuf ne produisait jamais de sauvegarde) ; et la section
« Limite importante » promettait la continuité de la règle des 4/12 mois
« dans les deux cas », alors qu'en cas B la sauvegarde reste sur le serveur
qu'on vient de perdre. Détail des corrections en fin de document.

**Version 6** (19/10/2026) — mise en accord avec le défaut d'intégrité du
déploiement découvert le 13/10/2026 (voir `VERA_THREAT_MODEL_COMPLETE.md`,
« Intégrité du déploiement ») : le modèle d'unité du dépôt dit désormais
`WorkingDirectory=/root/repo-push` (il disait `/root`), donc l'instruction de
l'étape 5 de la Partie 2 a changé ; et un contrôle de conformité
(`infra/verifier_deploiement.sh`) est ajouté à la fin des Parties 1 et 2, car
« le service est actif » ne prouve pas que le code servi est celui du dépôt.

**Version 7** (20/10/2026) — les trois secrets de l'unité (`VERA_DB_KEY`,
`VERA_ADMIN_HASH`, `VERA_SECRET_CREATION_COMPTE`) ne sont plus des lignes
`Environment=` de l'unité systemd : ils sont dans **`/etc/vera/vera.env`**
(propriétaire root, mode 600, dossier 700). Audit externe du 19/10/2026, F6 :
`systemctl cat` et `systemctl show` les affichaient en clair, le chemin par
lequel des secrets avaient déjà fuité le 31/07/2026. Conséquence pour ce
document : toute étape qui disait « éditer l'unité et remplacer la ligne
`Environment="VERA_..."` » dit maintenant « éditer `/etc/vera/vera.env` ». Les
**valeurs** de l'enveloppe ne changent pas ; seul l'endroit où on les pose.
`VERA_DOMAINE` et `VERA_ADMIN_USER` restent dans l'unité (ce ne sont pas des
secrets).

**Version 8** (20/10/2026) — l'accès SSH au serveur se fait **par clé**, plus
par mot de passe (`infra/sshd-durcissement.conf`). Conséquences pour ce
document : l'étape « se connecter en SSH » de la Partie 1 dit avec quoi se
connecter et que faire si la clé est perdue ; la Partie 2 dit comment poser la
clé et couper le mot de passe sur un serveur neuf. Le mot de passe root existe
toujours : il ne sert plus qu'à la **console web de l'hébergeur**, qui ne passe
pas par SSH.

---

## Ce que l'enveloppe doit contenir (six valeurs)

Référence unique — les mentions plus bas dans ce document ne recomptent plus
d'ordinal (« cinquième », « sixième »), pour ne pas se périmer à chaque ajout
futur :

1. `VERA_DB_KEY`
2. `VERA_ADMIN_USER`
3. `VERA_ADMIN_HASH`
4. `VERA_SECRET_CREATION_COMPTE`
5. `VERA_DOMAINE` — pas un secret, mais obligatoire au démarrage
6. `VERA_BACKUP_KEY` — fichier (`/root/.vera_backup_key`), pas une variable
   d'environnement de l'unité systemd

Où chacune se pose : les valeurs 1, 3 et 4 dans **`/etc/vera/vera.env`**, les
valeurs 2 et 5 dans l'unité (`systemctl edit --full`), la valeur 6 dans son
fichier à part.

---

## Avant de commencer : quel cas es-tu dans ?

- **Cas A — le serveur existe encore et répond**, mais le service est arrêté ou
  refuse de démarrer (secret perdu, serveur redémarré, erreur de configuration).
  → Va directement à la [Partie 1](#partie-1--cas-a-le-serveur-existe-encore).
- **Cas B — le serveur n'existe plus** (résilié, détruit, inaccessible) et il
  faut repartir sur une machine neuve.
  → Va à la [Partie 2](#partie-2--cas-b-repartir-sur-un-serveur-neuf).

**Limite importante :** cette procédure et l'enveloppe qui l'accompagne
permettent de **redémarrer le service** dans les deux cas. **Elle ne permet
toujours pas de reprendre une consultation active**, ni en cas A ni en cas
B : la sauvegarde ne contient que l'historique des clôtures passées, jamais
les votes ou jetons d'une consultation en cours — c'est un choix délibéré,
pas un oubli (voir l'en-tête de `sauvegarder_base.sh`). Un serveur perdu
pendant une consultation active signifie qu'elle est annulée et relancée
avec de nouveaux liens, dans les deux cas.

**La continuité de la règle des 4 consultations / 12 mois, elle, n'est
garantie que différemment selon le cas :**
- **Cas A** : garantie, la base et ses sauvegardes existent toujours sur le
  serveur.
- **Cas B** : **garantie seulement si une copie de la sauvegarde a été faite
  hors du serveur après la dernière clôture** — voir la section suivante.
  Sans cette copie, `sauvegarder_base.sh` tournait bien chaque nuit, mais son
  résultat disparaît avec le serveur perdu, comme tout le reste.

**Après toute rotation de `VERA_DB_KEY` sur le serveur réel, refaire
l'enveloppe.** Une copie séquestrée périmée bloque le démarrage exactement
comme une copie fausse — la procédure ne peut pas faire la différence.

### Après chaque clôture de consultation : une copie hors serveur

Le contenu de `historique_consultations` ne change qu'à une clôture —
`enregistrer_consultation_close()` est la seule fonction qui y écrit, en
dehors des migrations (`vera_persistance.py:865`). Entre deux clôtures,
toutes les sauvegardes de la nuit sont identiques : **une seule copie par
clôture suffit**, une copie régulière n'ajoute rien.

Depuis le téléphone, une fois le cron de 3h passé (ou tout de suite, voir la
variante ci-dessous) :
```
scp root@<serveur>:/root/sauvegardes_vera/vera_historique_*.db.enc .
```
Variante immédiate, si on ne veut pas attendre le lendemain matin — lancer le
script à la main juste après la clôture, puis copier :
```
ssh root@<serveur> "VERA_DB_PATH=/root/vera_state.db /usr/local/bin/sauvegarder_base.sh"
scp root@<serveur>:/root/sauvegardes_vera/vera_historique_*.db.enc .
```

Sans cette étape, une perte du serveur en cas B efface aussi la règle des
4/12 mois, pas seulement le service. Ce n'est pas une garantie d'anonymat
qui est en jeu : le code documente lui-même cette table comme « un
garde-fou de bonne foi, pas une contrainte » — la règle reste de toute
façon sous la responsabilité de l'organisation, pas de VERA
(`vera_persistance.py:865`, docstring de `enregistrer_consultation_close`).

---

## Partie 1 — Cas A : le serveur existe encore

1. Se connecter en SSH au serveur, **avec la clé** (le mot de passe est refusé
   depuis le 20/10/2026) :
   ```
   ssh root@<serveur>
   ```
   La phrase de passe demandée est celle de la clé, pas un mot de passe du
   serveur. **Clé perdue ou téléphone perdu** : ouvrir la console web de
   l'hébergeur (Hetzner Cloud, le serveur, « Console »), se connecter en root
   avec le mot de passe root — la console locale ne passe pas par SSH, donc
   n'est pas concernée par le refus du mot de passe — puis ajouter une nouvelle
   clé publique à `/root/.ssh/authorized_keys` (une ligne par clé, à la suite
   des autres). Ne jamais réactiver le mot de passe SSH pour dépanner : ajouter
   une clé suffit.
2. Vérifier l'état du service :
   ```
   sudo systemctl status vera-consultation.service
   ```
3. Le service n'écrit **pas** dans le journal systemd — l'unité redirige sa
   sortie vers un fichier, quel que soit `WorkingDirectory`
   (`StandardOutput=append:/root/consultation.log`, un chemin absolu, pas
   relatif à l'unité). `journalctl` ne montrera donc que les messages internes
   de systemd (« Main process exited… »), jamais la raison applicative.
   Regarder plutôt :
   ```
   sudo tail -n 50 /root/consultation.log
   ```
   Le service refuse de démarrer dans plusieurs cas ; le message exact dit
   lequel :
   - `VERA_DB_KEY ne correspond pas a l'ensemble des cles stockees` → la
     valeur actuelle ne correspond pas à la base existante. Remplacer par la
     valeur de l'enveloppe (étape suivante).
   - `VERA_DB_KEY non definie` → la variable est absente de
     `/etc/vera/vera.env` (ou ce fichier n'existe pas : dans ce cas le service
     ne démarre même pas, et `systemctl status` le dit).
   - `ni VERA_ADMIN_USER, ni VERA_ADMIN_HASH ne sont definis` → il manque un
     compte d'administration. Voir étape 5.
   - `VERA_DOMAINE vaut …` (sans `https://`) → corriger la variable
     `VERA_DOMAINE` dans l'unité, elle doit commencer par `https://`.
4. Éditer le fichier de secrets et poser la bonne valeur :
   ```
   sudo nano /etc/vera/vera.env
   ```
   Repérer la ligne `VERA_DB_KEY=...` (sans guillemets, sans `export`) et
   remplacer la valeur par celle de l'enveloppe. Sauvegarder, quitter
   l'éditeur, puis vérifier que les droits n'ont pas changé :
   ```
   sudo ls -l /etc/vera/vera.env      # doit afficher -rw------- root root
   ```
   `VERA_DOMAINE`, lui, n'est pas dans ce fichier : il est dans l'unité
   (`sudo systemctl edit --full vera-consultation.service`).
5. **Se donner un accès RH, si celui de l'enveloppe ne suffit pas.**
   L'enveloppe contient `VERA_ADMIN_HASH`, pas le mot de passe en clair — elle
   permet au *service* de démarrer, pas de s'y connecter. C'est la situation
   normale pour quiconque reprend le projet sans avoir jamais eu ce mot de
   passe, pas seulement un cas de mot de passe perdu. Deux façons d'obtenir un
   accès, indépendantes l'une de l'autre :
   - **Créer un nouveau compte RH** via `VERA_SECRET_CREATION_COMPTE` (aussi
     dans l'enveloppe), sans avoir besoin de l'ancien mot de passe :
     ```
     curl -X POST https://<domaine>/api/admin/creer_compte_rh \
       -H "Content-Type: application/json" \
       -d '{"identifiant":"<nouvel_identifiant>","mot_de_passe":"<nouveau_mot_de_passe>","secret_admin":"<VERA_SECRET_CREATION_COMPTE de l'enveloppe>"}'
     ```
   - **Ou remplacer directement `VERA_ADMIN_HASH`** dans `/etc/vera/vera.env`, avec une
     empreinte calculée depuis un clone du dépôt (voir Partie 2, étape 4) :
     ```
     python3 -c "from vera_admin_auth import generer_empreinte; print(generer_empreinte('nouveau-mot-de-passe'))"
     ```
     puis coller le résultat dans la ligne `VERA_ADMIN_HASH=` de
     `/etc/vera/vera.env` (étape 4 ci-dessus) et redémarrer.
   Ceci ne touche à aucun vote déjà enregistré — uniquement à qui peut se
   connecter comme RH.
6. Recharger et redémarrer :
   ```
   sudo systemctl daemon-reload
   sudo systemctl restart vera-consultation.service
   sudo systemctl status vera-consultation.service
   ```
7. Vérifier que le service répond réellement, pas seulement qu'il est
   « actif » :
   ```
   curl -s https://<le domaine configuré>/api/engagement_cles
   ```
   Une réponse JSON avec les clés `epsilon_par_publication` et
   `seuil_publication` confirme que le service tourne et sert les bonnes
   garanties. Puis, depuis le dossier du dépôt :
   ```
   bash infra/verifier_deploiement.sh
   ```
   Il doit afficher `CONFORME.` (le service peut être « actif » en servant du
   code périmé : ce contrôle le détecte, pas `systemctl status`). Si le
   domaine n'est pas `vera-consultation.fr`, le préfixer :
   `DOMAINE=<votre domaine> bash infra/verifier_deploiement.sh`.

   Une page d'erreur ou une absence de réponse veut dire que le
   problème n'était pas seulement le secret — s'arrêter là et documenter ce
   qui a été essayé, y compris le contenu de `/root/consultation.log`.

---

## Partie 2 — Cas B : repartir sur un serveur neuf

Reprend l'installation du `README.md`, mais avec deux adaptations que le
README ne couvre pas : faire correspondre les chemins réellement utilisés par
l'unité systemd (elle ne les déduit pas automatiquement), et poser un
certificat TLS pour le nouveau domaine.

**Toutes les commandes qui suivent supposent une connexion en root** (ou
`sudo -i` lancé au préalable). Sur une image Ubuntu cloud standard, la
connexion initiale se fait souvent avec l'utilisateur `ubuntu`, pas `root` —
dans ce cas, lancer `sudo -i` avant de commencer, sans quoi `cd /root` et les
commandes suivantes échouent dès l'étape 2.

### 1. Provisionner le serveur

- Linux récent (Ubuntu 24.04+ testé), 2 Go de RAM suffisent.
- Un nom de domaine pointé sur ce serveur.
- Paquets nécessaires à la compilation, absents d'une image minimale :
  ```
  sudo apt update
  sudo apt install -y build-essential python3-venv nginx certbot python3-certbot-nginx
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  source "$HOME/.cargo/env"
  rustup update stable
  ```
  Rust 1.85 ou plus récent est nécessaire — une version plus ancienne échoue à
  la compilation avec un message qui ne dit pas que la chaîne est trop
  ancienne.
- **Accès SSH par clé seulement.** Déposer d'abord sa clé publique
  (`ssh-copy-id` ou `cat ~/.ssh/id_ed25519.pub | ssh root@<serveur> "mkdir -p
  ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600
  ~/.ssh/authorized_keys"`), **vérifier** qu'une connexion par clé fonctionne,
  puis, sur le serveur :
  ```
  printf 'PasswordAuthentication no\nPermitRootLogin prohibit-password\n' > /etc/ssh/sshd_config.d/10-vera-durcissement.conf
  sshd -t && sshd -T | grep -E '^(passwordauthentication|permitrootlogin) '
  systemctl reload ssh
  ```
  Le nom en `10-` compte : `50-cloud-init.conf` réactive le mot de passe et
  gagne s'il est lu en premier (voir l'en-tête de
  `infra/sshd-durcissement.conf`). Garder la session ouverte et tester une
  seconde connexion avant de la fermer.
- **Un hébergeur différent de toute organisation qui utiliserait VERA pour
  elle-même** — condition documentée de la garantie du projet, pas un détail
  technique.

### 2. Récupérer le code, à un chemin qu'on retient

```
cd /root
git clone https://github.com/taha-vera/projet-vera-consultations-.git app
cd /root/app
pwd   # note ce chemin, il sert aux étapes 3, 5 et 7
```

### 3. Installer les dépendances et compiler le module de signature

```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pip install maturin
cd vera_blind_sig
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 maturin develop --release --locked
cd ..

which python3   # note ce chemin exact, il sert aux etapes 5 et 7, et a la Partie 3
```

**Pourquoi noter ces deux chemins explicitement :** l'unité systemd du dépôt
(`infra/vera-consultation.service`), le script `sauvegarder_base.sh` lui-même
(sa valeur par défaut interne), et la Partie 3 de ce document sont tous
écrits pour l'agencement de l'**ancien** serveur
(`/root/vera_blind_sig/.venv/bin/python3`). Ce nouveau serveur crée le venv
**à la racine du clone** (`.venv`, pas `vera_blind_sig/.venv`) — c'est le
chemin obtenu ici qu'il faut utiliser partout ci-dessous, jamais l'ancien
chemin codé en dur.

### 4. Préparer les secrets

Quatre viennent de l'enveloppe (à recopier tels quels, sans les modifier ; trois
iront dans `/etc/vera/vera.env`, un — l'identifiant — dans l'unité), et
une cinquième valeur — pas un secret, mais obligatoire — dépend du nouveau
domaine (liste complète des six valeurs de l'enveloppe en tête de document) :

- `VERA_DB_KEY` <<< À REMPLACER >>> (valeur de l'enveloppe)
- `VERA_ADMIN_USER` <<< À REMPLACER >>> (valeur de l'enveloppe)
- `VERA_ADMIN_HASH` <<< À REMPLACER >>> (valeur de l'enveloppe)
- `VERA_SECRET_CREATION_COMPTE` <<< À REMPLACER >>> (valeur de l'enveloppe)
- `VERA_DOMAINE` <<< À REMPLACER >>> (`https://` + le nom de domaine réel de
  ce serveur — **pas** forcément le même que l'ancien). Cette valeur sert à
  la fois de règle CORS et de base des liens de vote envoyés aux participants.
  Une valeur fausse laisse le service démarrer et répondre au `curl` de
  vérification, mais chaque lien de vote généré pointerait vers le mauvais
  domaine, et le tableau de bord serait bloqué par CORS.

**Sur `VERA_DB_KEY` en cas B précisément :** si la base de l'ancien serveur
n'a pas pu être récupérée (disque perdu), cette valeur ne sert à rien de
particulier au premier démarrage — il n'y a pas encore de clé RSA chiffrée à
déchiffrer sur une base neuve. La poser quand même garde la compatibilité
avec toute donnée récupérée plus tard.

**`VERA_BACKUP_KEY` est séparée des quatre ci-dessus** — ce n'est pas une
variable de l'unité systemd, mais un fichier lu directement par
`sauvegarder_base.sh`. Recopier la valeur de l'enveloppe (pas la régénérer)
dans ce fichier, puis verrouiller ses permissions :
```
nano /root/.vera_backup_key   # <<< À REMPLACER >>> coller la valeur de l'enveloppe, une seule ligne
chmod 600 /root/.vera_backup_key
```
Sans cette étape, `sauvegarder_base.sh` refuse de tourner (il le dit
explicitement), et une sauvegarde récupérée depuis l'ancien serveur (voir
Partie 3) resterait illisible.

Si l'enveloppe est incomplète ou illisible, ces secrets (hors `VERA_DOMAINE`)
peuvent être régénérés à neuf — ce sont alors de **nouveaux** secrets, sans
lien avec les anciens, et toute donnée chiffrée de l'ancien serveur resterait
illisible (y compris les sauvegardes existantes, si `VERA_BACKUP_KEY` est
régénérée plutôt que restaurée) :
```
python3 -c "import secrets; print(secrets.token_hex(32))"          # VERA_DB_KEY, ou VERA_BACKUP_KEY
openssl rand -base64 32                                            # VERA_SECRET_CREATION_COMPTE
python3 -c "from vera_admin_auth import generer_empreinte; print(generer_empreinte('votre-mot-de-passe'))"  # VERA_ADMIN_HASH
```

### 5. Poser la configuration serveur

Obtenir un certificat pour le nouveau domaine (remplace les chemins Let's
Encrypt déjà présents dans `infra/nginx-vera-consultation.conf`, qui pointent
sur l'ancien nom de domaine) :
```
sudo certbot certonly --nginx -d <votre-domaine>
```

```
sudo cp infra/nginx-vera-consultation.conf /etc/nginx/sites-available/vera-consultation
sudo ln -s /etc/nginx/sites-available/vera-consultation /etc/nginx/sites-enabled/
```
Dans ce fichier, remplacer : le `server_name` (il apparaît **deux fois** —
dans le bloc principal et dans le bloc de redirection HTTP, ne pas oublier le
second) et les trois blocs `if ($host = ...)` par le nouveau domaine, et les
deux chemins `ssl_certificate` / `ssl_certificate_key` par ceux que
`certbot` vient de créer (`/etc/letsencrypt/live/<votre-domaine>/`). **Ne pas
toucher** à `access_log off` (Nginx) ni à `error_log crit` (posé au niveau du
bloc `server`, donc valable pour toutes les routes y compris celles du
vote) — ils ferment un canal de corrélation documenté
(VERA_THREAT_MODEL_COMPLETE.md, porte 26).

Copier la page d'accueil statique — sans ça, la racine du domaine répond 404 :
```
sudo mkdir -p /var/www/vera
sudo cp index.html /var/www/vera/
```

```
sudo cp infra/vera-consultation.service /etc/systemd/system/vera-consultation.service
sudo systemctl edit --full vera-consultation.service
```
Dans ce fichier :
- Remplacer `WorkingDirectory=/root/repo-push` (valeur de l'ancien serveur)
  par le chemin noté à l'étape 2. **Ne jamais le laisser à `/root`** : le
  service chargerait alors du code qui n'est pas celui du clone, sans aucune
  erreur (défaut du 13/10/2026).
- Remplacer l'interpréteur dans `ExecStart` par le chemin noté à la fin de
  l'étape 3.
- Remplacer le `CHANGER_MOI` de `VERA_ADMIN_USER` par l'identifiant de
  l'étape 4, et remplacer la valeur de `VERA_DOMAINE` par le domaine du
  nouveau serveur (`https://` + nom réel).
- **Ne pas** mettre les trois secrets dans l'unité : ils vont dans le fichier
  créé juste après.
**Ne jamais** recommitter ce fichier avec des valeurs réelles dedans.

Créer le fichier des trois secrets, **avant** de démarrer le service (sans lui,
systemd refuse de le lancer) :
```
sudo install -d -m 700 /etc/vera
sudo cp infra/vera.env.exemple /etc/vera/vera.env
sudo chmod 600 /etc/vera/vera.env
sudo nano /etc/vera/vera.env   # <<< À REMPLACER >>> les trois CHANGER_MOI par les valeurs de l'enveloppe
sudo ls -l /etc/vera/vera.env  # doit afficher -rw------- root root
```
Format : `NOM=valeur`, une par ligne, **sans guillemets ni `export`**. Le `$`
de `VERA_ADMIN_HASH` (`sel$hash`) se recopie tel quel : systemd ne développe
aucun `$` dans ce type de fichier.

### 6. Démarrer et vérifier

```
sudo systemctl daemon-reload
sudo systemctl enable --now vera-consultation.service
sudo systemctl status vera-consultation.service
sudo nginx -t && sudo systemctl reload nginx
curl -s https://<votre domaine>/api/engagement_cles
curl -s https://<votre domaine>/
```

Puis le contrôle de conformité, qui vérifie que ce qui est SERVI est bien ce
qui est dans le clone (répertoire de travail du processus, module Rust compilé
après ses sources, fichiers statiques, configuration nginx réellement
rechargée) :
```
cd <chemin du clone>
DOMAINE=<votre domaine> bash infra/verifier_deploiement.sh
```
Il doit se terminer par `CONFORME.` Toute ligne `ECART` dit quoi corriger.

La première réponse doit être un JSON avec `epsilon_par_publication` et
`seuil_publication`. La seconde doit rendre la page d'accueil, pas une 404.
Si l'une des deux échoue, regarder `sudo tail -n 50 /root/consultation.log`
(chemin fixe, indépendant de `WorkingDirectory` — voir Partie 1, étape 3) et
`sudo journalctl -u vera-consultation.service -n 50` pour les erreurs de
démarrage systemd elles-mêmes (chemin d'interpréteur incorrect, par exemple).

### 7. Mettre en place la sauvegarde automatique (sur ce nouveau serveur aussi)

Le script `sauvegarder_base.sh` du dépôt (dans `infra/`) n'est pas relancé
tout seul après une reprise en cas B — recommencer sa mise en place :
```
sudo cp infra/sauvegarder_base.sh /usr/local/bin/sauvegarder_base.sh
sudo chmod +x /usr/local/bin/sauvegarder_base.sh
sudo crontab -e
```
Ajouter, en remplaçant `<chemin du clone>` par celui noté à l'étape 2 (le
même chemin que celui utilisé pour l'interpréteur Python à l'étape 3) :
```
0 3 * * * VERA_PYTHON=<chemin du clone>/.venv/bin/python3 VERA_DB_PATH=/root/vera_state.db /usr/local/bin/sauvegarder_base.sh >> /root/sauvegarde_vera.log 2>&1
```
**`VERA_PYTHON` doit toujours être posé explicitement ici.** Le script a sa
propre valeur par défaut, mais elle pointe vers l'ancien serveur
(`/root/vera_blind_sig/.venv/bin/python3`) — si la ligne ci-dessus omet
`VERA_PYTHON`, le script échoue chaque nuit sans bruit (l'erreur ne va que
dans `/root/sauvegarde_vera.log`, jamais consulté sauf à le chercher).
`VERA_DB_PATH` est déjà `/root/vera_state.db` par défaut dans le script ;
la valeur est répétée ici pour ne rien laisser à l'implicite, pas parce
qu'une autre valeur aurait un sens — ce chemin ne dépend pas de l'emplacement
du clone.

---

## Partie 3 — Restaurer une sauvegarde

**Ce que ça restaure, précisément :** le registre des consultations déjà
clôturées (quel groupe, à quelle date), pour que la règle des 4
consultations / 12 mois continue de s'appliquer correctement. **Ça ne
restaure pas une consultation active** — la sauvegarde ne contient jamais
de vote, de jeton ni de clé (voir l'en-tête de `sauvegarder_base.sh`). Si
le serveur est tombé pendant une consultation en cours, elle est perdue
dans tous les cas ; cette restauration évite seulement qu'une nouvelle
consultation, une fois relancée, ignore les clôtures précédentes.

À utiliser en cas B, après l'étape 6, si une sauvegarde de l'ancien serveur a
pu être récupérée — c'est-à-dire si la copie hors serveur après chaque
clôture (voir « Après chaque clôture de consultation », plus haut) a bien
été faite. Sans cette copie, il n'y a rien à restaurer ici : le fichier
vivait uniquement sur le serveur perdu.

1. Déchiffrer la sauvegarde choisie avec `VERA_BACKUP_KEY` (pas
   `VERA_DB_KEY` — ce n'est pas la même clé) :
   ```
   openssl enc -d -aes-256-cbc -pbkdf2 \
     -pass "file:/root/.vera_backup_key" \
     -in vera_historique_<date>.db.enc \
     -out /root/historique_recupere.db
   ```
   Une mauvaise valeur de `VERA_BACKUP_KEY` fait échouer cette commande
   (`bad decrypt`), mais **laisse quand même un fichier de sortie non vide**.
   Ne pas continuer si un message d'erreur apparaît ici — l'étape 2 le
   confirme de toute façon, mais autant s'arrêter tout de suite.
2. Vérifier que le fichier obtenu est lisible, avec l'interpréteur Python
   noté à l'étape 3 de la Partie 2 (**pas** `/root/vera_blind_sig/...`, cet
   ancien chemin n'existe pas sur ce serveur neuf) :
   ```
   <chemin du clone>/.venv/bin/python3 -c "import sqlite3; c=sqlite3.connect('/root/historique_recupere.db'); print(c.execute('SELECT * FROM historique_consultations').fetchall())"
   ```
3. Arrêter le service, importer les lignes dans la nouvelle base, puis
   redémarrer (même interpréteur qu'à l'étape 2) :
   ```
   sudo systemctl stop vera-consultation.service
   <chemin du clone>/.venv/bin/python3 -c "
   import sqlite3
   src = sqlite3.connect('/root/historique_recupere.db')
   dst = sqlite3.connect('/root/vera_state.db')
   lignes = src.execute('SELECT groupe, close_unix FROM historique_consultations').fetchall()
   dst.executemany('INSERT OR IGNORE INTO historique_consultations (groupe, close_unix) VALUES (?, ?)', lignes)
   dst.commit()
   "
   sudo systemctl start vera-consultation.service
   ```
4. Vérifier comme à l'étape 6 de la Partie 2.

Cette étape suppose que la nouvelle base (`/root/vera_state.db`) existe déjà
— c'est-à-dire après l'étape 6 de la Partie 2, pas avant.

---

## Ce que cette procédure ne couvre toujours pas

- **Une consultation active ne survit à la perte du serveur dans aucun des
  deux cas.** Choix délibéré depuis la version 4, pas un oubli — voir
  l'en-tête de `sauvegarder_base.sh`. Fermer ce point demanderait de
  resauvegarder des données par vote, ce qui rouvrirait exactement la fuite
  que la version 4 vient de fermer.
- **La continuité de la règle des 4/12 mois en cas B dépend d'une étape
  manuelle** (copie hors serveur après chaque clôture, voir plus haut). Si
  elle est oubliée avant la perte du serveur, il n'y a rien à restaurer en
  Partie 3.
- Elle n'a été relue en détail que par des audits ciblés successifs et des
  tests hors d'une machine réelle — jamais par une reprise complète sur un
  vrai serveur neuf. Tant que ce test grandeur nature n'a pas eu lieu, la
  considérer comme sérieusement revue, pas comme une garantie.

## Corrections apportées le 20/10/2026 (version 8)

- **Accès SSH par clé uniquement.** Le mot de passe root, qui avait fuité dans
  une conversation, n'est plus acceptable par SSH. Modifié : l'en-tête, l'étape 1
  de la Partie 1 (avec le cas « clé perdue » : console web de l'hébergeur), l'étape
  1 de la Partie 2 (pose de la clé et du fichier de durcissement).
- Vérifié sur le serveur de production : `sshd -T` donne
  `passwordauthentication no`, la connexion par mot de passe est refusée
  (`Permission denied (publickey)`) et celle par clé fonctionne.

## Corrections apportées le 20/10/2026 (version 7)

- **Les trois secrets quittent l'unité** pour `/etc/vera/vera.env` (audit F6).
  Modifié : l'en-tête, la liste de l'enveloppe (où poser chaque valeur), le
  diagnostic et les étapes 4 et 5 de la Partie 1, les étapes 4 et 5 de la
  Partie 2 (création du fichier). Le contrôle de conformité vérifie désormais
  l'existence du fichier, ses droits (root, 600, dossier 700) et ses noms, sans
  jamais lire une valeur.
- **Rotation d'un secret** (par exemple `VERA_SECRET_CREATION_COMPTE`) : éditer
  `/etc/vera/vera.env`, puis `sudo systemctl restart vera-consultation.service`
  — `daemon-reload` n'est pas nécessaire pour un `EnvironmentFile`, mais
  inoffensif.

## Corrections apportées le 19/10/2026 (version 6)

- **`WorkingDirectory` (Partie 2, étape 5).** Le texte disait de remplacer
  `/root` ; le modèle d'unité du dépôt vaut `/root/repo-push` depuis le
  16/10/2026. Réécrit, avec l'avertissement de ne jamais le laisser à `/root`.
- **Contrôle de conformité ajouté** à la fin de la Partie 1 (étape 7) et de la
  Partie 2 (étape 6), avec `infra/verifier_deploiement.sh`.
- Rien d'autre n'a changé : la copie hors serveur après clôture (section
  « Après chaque clôture de consultation ») a
  été faite pour la première fois le 19/10/2026, clé de sauvegarde comprise
  dans l'enveloppe.

## Corrections apportées le 23/09/2026 (audit ciblé sur le document lui-même)

- **Chemins Python de la Partie 3 et du cron (bloquant).** Ils supposaient
  l'agencement de l'ancien serveur (`/root/vera_blind_sig/.venv/...`), alors
  que la Partie 2 crée le venv à la racine du clone. Vérifié par exécution
  réelle : la Partie 3 échouait silencieusement (le service redémarrait sans
  qu'aucune ligne ne soit importée, et la vérification de l'étape 4 ne le
  détecte pas puisqu'elle ne teste pas l'historique) ; le cron d'un serveur
  neuf échouait chaque nuit sans bruit. Remplacé par des références au chemin
  noté à l'étape 3 de la Partie 2, partout où l'ancien chemin était codé en
  dur — y compris dans la valeur par défaut interne du script, signalée
  explicitement pour que `VERA_PYTHON` soit toujours posé dans la ligne cron.
- **« Limite importante » promettait la continuité de la règle des 4/12 mois
  « dans les deux cas » (sérieux).** En cas B, la sauvegarde reste sur le
  serveur qu'on vient de perdre — la promesse ne tenait qu'en cas A. Ajout
  d'une étape manuelle de copie hors serveur après chaque clôture (le
  contenu ne change qu'à ce moment-là, une copie régulière n'aurait rien
  ajouté), et correction de la Partie 3 qui renvoyait vers une note absente
  du script pour cette copie.
- **Deux paragraphes « Version 4 » redondants et partiellement
  contradictoires** (l'un disait que la sauvegarde ne contenait plus que
  `historique_consultations`, l'autre ajoutait à tort `question_active`) :
  fusionnés en un seul, conforme à ce que le script fait réellement
  (vérifié : une seule table dans une sauvegarde déchiffrée).
- **Valeur de `VERA_DB_PATH` proposée dans la ligne cron, ambiguë** (« chemin
  du clone ou /root/vera_state.db » — la première option pointerait vers un
  dossier, pas une base) : fixée à `/root/vera_state.db`, seule valeur
  correcte quel que soit l'emplacement du clone.
- **Décompte des valeurs de l'enveloppe incohérent** selon l'endroit du
  document (« quatre », « cinquième » utilisé deux fois pour deux valeurs
  différentes) : remplacé par une liste unique de référence en tête de
  document, plus recomptée nulle part ailleurs.
- **Absence de consigne sur la connexion root/sudo** en Partie 2 et Partie 3,
  alors que certaines commandes l'omettent : ajout d'une note explicite en
  tête de Partie 2.
- Imprécisions mineures : le chemin du journal applicatif est absolu et ne
  dépend pas de `WorkingDirectory` (corrigé en Partie 1 et Partie 2) ; le
  fichier nginx contient deux occurrences de `server_name`, pas une ; la
  directive `error_log crit` est posée au niveau du bloc `server`, pas par
  route (sans conséquence sur la consigne de ne pas y toucher, précisé pour
  exactitude) ; désambiguïsation entre la numérotation de version de ce
  document et celle, distincte, de l'en-tête du script (« VERSION 1 » /
  « VERSION 2 »).

## Corrections apportées le 22/09/2026, deuxième passe (audit ciblé sur le script)

- **Le script sauvegardait toute la base chaque nuit** (compteurs, jetons,
  clé RSA). Un audit ciblé a montré que ça rétablissait, à l'échelle du
  jour, la fuite que le projet a fermée en abandonnant le mode WAL — et que
  réduire la rétention à une seule sauvegarde n'aurait rien changé, la base
  vivante formant déjà la paire comparable avec elle. Remplacé par un
  export d'une seule table non sensible (`historique_consultations`).
  Conséquence assumée : une consultation active n'est plus recouvrable,
  seulement le registre des clôtures passées (Partie 3, réécrite).
- Vérification des permissions du fichier de clé (600), pas seulement de
  sa présence.
- Écriture atomique : chiffrement vers un `.tmp`, vérifié par
  déchiffrement réel avant d'être renommé en fichier final — une
  sauvegarde tronquée ne peut plus être comptée comme bonne.
- Effacement du fichier temporaire en clair par `shred` plutôt que `rm`
  simple.
- Testé de bout en bout avec des données sensibles factices dans la base
  source, pour confirmer que seule `historique_consultations` ressort du
  fichier chiffré.

## Corrections apportées le 22/09/2026, première passe (sauvegarde)

- Ajout de `sauvegarder_base.sh` : sauvegarde chiffrée quotidienne, avec
  rotation sur 7 jours, et instructions de restauration (Partie 3). Testé
  de bout en bout avant livraison, et testé aussi sur l'absence de
  `VERA_BACKUP_KEY` pour confirmer que le script refuse proprement plutôt
  que d'échouer en silence. *(Cette première version sauvegardait toute la
  base — voir la correction du 22/09 deuxième passe, qui la remplace.)*
- Ajout de `VERA_BACKUP_KEY` comme valeur supplémentaire à séquestrer,
  distincte des quatre variables de l'unité systemd.
- Le script utilise le module `sqlite3` de Python plutôt que l'outil en
  ligne de commande du même nom, qui n'est installé nulle part dans ce
  projet — évite d'introduire une dépendance système qui n'existait pas.

## Corrections apportées le 21/09/2026 (audit ciblé)

- Cas A, diagnostic : `journalctl` ne montre rien d'utile (sortie redirigée
  vers un fichier) — remplacé par `tail` sur le bon fichier, et le message
  d'erreur cité était le mauvais (un simple avertissement, pas celui qui
  bloque réellement le démarrage).
- Cas A, étape 5 : reformulée comme chemin normal pour un successeur sans
  mot de passe, pas comme cas exceptionnel — et une deuxième méthode
  ajoutée (`creer_compte_rh`), qui ne nécessite aucun accès shell.
- Cas B : les chemins de clonage et du venv ne correspondaient pas à ceux
  attendus par l'unité systemd copiée telle quelle — le service ne pouvait
  pas démarrer. Remplacé par une étape qui fait correspondre l'unité au
  chemin réellement utilisé, quel qu'il soit.
- Cas B : ajout des paquets système et de l'installation de Rust, absents
  de la version précédente comme du README.
- Cas B : ajout de la provision du certificat TLS (`certbot`) et de la
  copie de la page d'accueil statique, absentes toutes les deux.
- Ajout de `VERA_DOMAINE` comme valeur supplémentaire à poser, oubliée de
  la liste des « secrets » alors qu'elle est obligatoire.
- Correction de deux citations inexactes : la clé JSON est
  `epsilon_par_publication`, pas `epsilon` ; la garde sur les journaux
  applicatifs est documentée dans `VERA_THREAT_MODEL_COMPLETE.md` (porte
  26), pas dans `LIMITS.md`.
- Correction d'une contradiction interne (« trois » valeurs annoncées,
  quatre listées).
