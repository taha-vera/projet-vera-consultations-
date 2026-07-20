# Plan : refactor Modele B + cles par departement

## ETAT AU 20/07 (soir) -- REPRENDRE ICI
Couches 1-2 FAITES, testees sur base isolee, commitees (b550fb5) mais PAS
portees en prod (incompatibles avec gestionnaire encore mono-cle).
- Couche 1 : schema cle_rsa_active departement PRIMARY KEY + migration auto
  idempotente (_migrer_schema_cles dans initialiser()). VALIDE bout-en-bout.
- Couche 2 : persistance chiffree par departement (persister/charger_cle_rsa_
  chiffree(departement,...), charger_toutes_cles_chiffrees(), effacer_cle_rsa
  efface tout). Vestiges morts supprimes. Test test_couche2.py OK.
- DB_PATH configurable via VERA_DB_PATH (isolation bac a sable posee, ne PAS
  perdre : sans ca un DROP de test toucherait la base de prod).
PROCHAINE ETAPE = COUCHE 3 : le gestionnaire (vera_signature_manager.py).
  self._cle_privee_der scalaire -> dict {departement: (priv,pub)}. Generation
  a la volee (1ere demande d'un departement). UN timer de destruction groupee
  a ouverture+DUREE_VIE (decision actee). Rechargement au boot via
  charger_toutes_cles_chiffrees(). ATTENTION : etat memoire + threads + timer,
  concentration requise, faire en session fraiche.
Rappel test : lancer avec VERA_DB_KEY (depuis systemd) + VERA_DB_PATH isole +
  /root/vera_blind_sig/.venv/bin/python3. Bac a sable = /root/vera_test.
Rappel mobile : heredocs cassent, PREFERER fichiers .py + python3 fichier.py.


## Contexte
Suite du refactor crypto d'unlinkability. Le tour multi-IA (Copilot, ChatGPT,
Gemini, Mistral, Fable 5) a tranche DEUX decisions structurantes qui rendent
caduque une partie des briques 5-8 initialement prevues.

## Decision 1 : MODELE B (jeton de vote opaque), pas Modele A
3 IA disaient A, Fable 5 disait B. Verdict le plus dur retenu.
Raison decisive (Fable 5) : en Modele A, le votant finit avec (M, signature) ou
M contient sa reponse EN CLAIR + signature verifiable par tous = RECU DE VOTE
transferable. Un RH coercitif peut exiger "montre ton bulletin signe oui".
Le Modele A FABRIQUE l'outil de coercition. Adversaire n1 de VERA = le RH => B.

Flux Modele B :
- Temps 1 (fait, briques 1-4) : RH distribue jetons d'autorisation par SMS.
- Temps 2 (emargement) : client genere un secret K aleatoire (128 bits),
  l'aveugle, presente (jeton_autorisation, K_aveugle). Serveur consomme le
  jeton (registre 1, atomique), signe K_aveugle AVEC LA CLE DU DEPARTEMENT,
  renvoie la signature aveugle. Client finalise -> detient (K, signature(K)).
  K ne dit RIEN du vote.
- Temps 3 (vote) : client envoie (K, signature(K), reponse) sur /api/repondre.
  Serveur, EN UNE SEULE TRANSACTION : verifie signature(K) sous la cle publique
  du departement -> verifie H(K) absent du registre 2 -> valide reponse dans la
  liste autorisee -> enregistre (reponse, departement) + insere H(K) registre 2
  -> UN SEUL COMMIT. Reponse invalide -> 400, jeton de vote survit, retry OK.

## Decision 2 : UNE PAIRE DE CLES PAR DEPARTEMENT (trouvaille du tour)
Ferme la porte "departement auto-declare" (Fable 5) : si le departement etait
un champ ecrit par le votant, il serait usurpable (pollution de cohortes,
manip K_MIN, reouverture partielle Porte 7 differencing). Solution : le
departement n'est PAS dans le message ; il est PROUVE PAR LA CLE. Le serveur
signe avec la cle du departement porte par le jeton d'autorisation (registre 1,
que le serveur controle). Au comptage, la signature ne verifie que sous la
bonne cle publique => appartenance prouvee sans identite.
Cout en anonymat : l'ensemble d'anonymat = le departement. C'est deja la
granularite de cohorte et de K_MIN => AUCUN recul reel.

## Decision 3 : departements CREES AU FIL DE L'EAU (tranche ce jour)
Pas de declaration a l'ouverture. Le champ departement de generer_autorisations
est deja un texte libre (brique 4). La cle d'un departement est creee la
PREMIERE FOIS que le RH genere des autorisations pour ce departement (dans la
brique 4), puis reutilisee. A trancher a froid : destruction groupee a
ouverture+DUREE_VIE (probable, plus simple) vs duree de vie par cle.

## Les 4 obligations de Fable 5 (Modele B)
1. Cle dediee par consultation ET par departement (jamais partagee ailleurs).
2. Deduplication registre 2 sur H(K) [= H(M) en modele B, K est le message].
   PAS H(signature) : RSA-PSS Randomized est probabiliste, plusieurs signatures
   valides pour un meme K.
3. Cache d'idempotence sur la phase de signature : jeton -> (K_aveugle,
   signature_aveugle) pour permettre retry si crash/reseau apres consommation
   du jeton (sinon electeur brule son jeton sans recevoir sa signature).
   SUR pour l'unlinkability : le serveur ne connait pas le facteur
   d'aveuglement r, ne peut relier signature_aveugle a signature finale.
4. Depense du jeton de vote + enregistrement reponse = UNE SEULE TRANSACTION
   SQLite, UN commit. (= bug historique du double-commit non-atomique. Zone de
   blessure connue. A ne PAS recreer.)

## Invariant reformule (Fable 5)
Ancien : "aucun lien jeton<->signature stocke".
Nouveau : "aucun lien jeton<->signature FINALE". Le lien vers la forme
aveuglee (cache d'idempotence) est inoffensif ET necessaire.

## Les 4 couches a modifier (chantier structurel)
Etat actuel = MONO-CLE par construction :
- Table SQLite cle_rsa_active : PRIMARY KEY fixe id=1 (une seule ligne).
- charger_cle_rsa_chiffree : WHERE id=1.
- ouvrir_consultation : une paire generee, UN timer de destruction.
- gestionnaire : self._cle_privee_der scalaire (pas un dict).

A refactorer :
1. Schema SQLite : cle_rsa_active -> multi-lignes, PRIMARY KEY = departement.
2. Persistance : persister/charger par departement (+ charger_tous au boot).
3. Gestionnaire : dict {departement: (priv, pub, ts)}, generation a la volee,
   destruction de N cles, gestion timer(s).
4. Briques 2/3/4 : signer_aveugle route selon departement du jeton ;
   cle_publique?departement=X expose la bonne cle ; generer_autorisations cree
   la cle du departement si absente.

ATTENTION : couche la plus sensible du systeme (cle privee, VERA_DB_KEY, Fernet,
destruction memoire). Erreur silencieuse possible : cle non detruite, mal
chiffree, ou rechargee pour le mauvais departement. A faire en session FRAICHE.

## Etat des briques (a jour)
Fait et en prod : brique 1 (registre autorisation), 2 (signer_aveugle),
3 (cle_publique), 4 (generer_autorisations), 5 preuve logique client HTTP.
MAIS 2/3/4 sont MONO-CLE => a adapter au multi-departement.
Caduc / a refaire pour Modele B : brique 5b (client fait signer K opaque, pas
le bulletin), 6 (verif empreinte cle), 7 (/api/repondre transactionnel),
8 (bascule).

## Question ouverte pour la prochaine session
- Destruction des cles : groupee (ouverture+DUREE_VIE) ou par cle ? (probable: groupee)
- Un timer global ou N timers ? (probable: un balayage groupe)
- La brique 5 preuve (brique5_test_client.mjs) doit etre refaite version B :
  faire signer K opaque, recuperer cle du departement via /api/cle_publique?departement=X.
