# Améliorations futures

Points identifiés lors des audits (notamment Fable 5, 18/07/2026) qui sont
**réels mais non urgents** : ce ne sont pas des bugs qui menacent la production,
mais des renforcements de tests et de validation. À traiter proprement sur un
environnement de test, pas en direct sur la production.

## Tests à ajouter

1. **Anti-rejeu persistant (Porte 14) — priorité haute.**
   `test_persistance.py` ne teste pas `persister_token_consomme` /
   `charger_tokens_consommes`. Or c'est le scénario clé de la Porte 14 :
   redémarrage du serveur → un token déjà consommé ne doit pas pouvoir être
   rejoué. Ajouter : persister une empreinte, recharger, vérifier sa présence ;
   puis un test d'intégration (base temporaire) qui consomme un token, détruit
   l'instance du gestionnaire, en recrée une, et vérifie que le rejeu est refusé.

2. **Chiffrement au repos.** Aucun test ne vérifie que les votes sont chiffrés
   dans le fichier .db. Test simple : lire les octets bruts du .db et vérifier
   que b"oui", b"dept_A" n'y apparaissent pas. Idem après
   effacer_etat_consultation() : vérifier que les lignes supprimées ne restent
   pas dans les pages libres/WAL (secure_delete ou VACUUM).

3. **Mauvaise clé de déchiffrement.** Recharger la base avec une VERA_DB_KEY
   différente doit échouer proprement (c'est le cœur de la Porte 11 : voler le
   .db sans la clé ne donne rien). Aucun test ne le vérifie actuellement.

4. **Accumulation du budget epsilon.** test_epsilon_budget consomme toujours le
   budget entier en un appel. Ajouter : budget 0.5, consommer 0.2 puis 0.2,
   vérifier restant=0.1, puis 0.2 refusé. Teste l'accumulation (+=), pas juste
   l'écrasement. Ajouter aussi le cas flottant (5×0.1 sur 0.5).

5. **Tests de concurrence.** Aucun test d'accès simultané, alors que le code est
   verrouillé partout et qu'un bug de boucle infinie sous verrou global a déjà
   existé (corrigé mais sans test de régression).

## Validations de code à ajouter

6. **Budget : refuser les coûts ≤ 0.** consommer("A", -1.0) augmente le budget
   (remboursement), coût 0 autorise l'infini. Ajouter dans consommer() :
   `if epsilon_requete <= 0: raise ValueError`.

7. **Décodeur de token : valider les types.** decoder_token_depuis_url vérifie
   la présence des champs mais pas leur type. (Le crash TypeError qui en
   résultait est déjà corrigé côté verifier_et_consommer le 18/07, mais valider
   les types dès le décodage serait plus propre.)

## Raffinements

8. **Tolérances test_precision_kmin.** Vérifier d'abord si np.random.seed a un
   effet réel (OpenDP RNG probablement non-seedable). Puis resserrer les
   tolérances : calculer l'erreur-type Monte-Carlo (bootstrap sur les 3000
   erreurs) et fixer tol = max(3·SE, 0.25) au lieu du ±0.8 forfaitaire, pour
   détecter une dérive fine et pas seulement une catastrophe.

9. **Isolation de test plus robuste.** Remplacer le patch de builtins.__import__
   dans test_signature_production par une variable d'environnement
   (VERA_SANS_PERSISTANCE=1) lue par le module — plus propre sous pytest.

## Cycle de vie de la clé (à spécifier puis tester)

10. Après _detruire_cle_privee() (expiration 48h), la clé publique reste :
    verifier_et_consommer peut-il encore accepter des tokens ? Comportement à
    spécifier explicitement, puis tester.


## CHANTIER MAJEUR -- Unlinkability du votant (crypto cote client)

**Gravite : haute. Touche la promesse centrale "anonymat prouve".**

Probleme identifie le 18/07/2026 (audit Fable 5, lecture bout-en-bout) :
la signature aveugle ne produit AUCUNE unlinkability dans l'architecture
actuelle. generer_token_signe() execute les 3 etapes (aveugler + signer +
finaliser) cote serveur ; le client (static/*.html) ne fait aucune crypto.
Le serveur produit donc le token complet et connait l'empreinte
SHA256(message+signature) qui sera consommee -> il peut relier identite et
acte de vote. Le CONTENU des votes reste protege (agregats bruites), mais la
non-liaison identite<->participation, elle, n'est pas prouvee.

Correctif (architectural, PAS un patch) : deplacer aveuglement +
finalisation dans le navigateur du votant.

Faisabilite etablie :
- Serveur : blind-rsa-signatures 0.17 (Rust), variante SHA384-PSS-Randomized (RFC 9474)
- Client : blindrsa-ts (Cloudflare) supporte la MEME variante -> interoperable
- Seule signer_aveugle doit rester cote serveur

Etapes du chantier :
1. Pont crypto : prouver qu'un message aveugle en JS (blindrsa-ts) est signe
   par la lib Rust et valide. Test de faisabilite AVANT tout le reste.
2. Endpoints serveur : /api/cle_publique + /api/signer_aveugle (recoit un
   message DEJA aveugle, ne voit jamais le message final).
3. Client JS (vote.html) : aveugle, envoie l'aveugle, recoit la sig aveugle,
   definalise, obtient le token -- le serveur ne l'a jamais vu.
4. POINT DUR (conception) : autorisation du votant. Aujourd'hui le RH genere
   et distribue les tokens. Dans le nouveau modele, le votant fabrique son
   token -> comment prouver qu'il a le droit de voter (une fois) SANS que le
   serveur puisse lier autorisation et token final ? Probleme classique du
   vote anonyme, solutions connues (jeton d'autorisation a usage unique,
   separation emetteur/signataire) mais c'est la vraie complexite.
5. Tests bout-en-bout sur environnement isole, puis bascule.

Ampleur : plusieurs jours de travail concentre. Le plus gros morceau de VERA.
A traiter comme un projet dedie, pas entre deux taches.
### Obstacle sjcl : LEVE (verifie le 18/07 soir)
Enquete sur node_modules/@cloudflare/blindrsa-ts : sjcl n'est utilise QUE pour
l'arithmetique grands nombres (sjcl.bn, sjcl.codec, sjcl.random, i2osp/os2ip,
inversion modulaire, generation de premiers). AUCUN appel a sjcl.ecc /
basicKey / courbe elliptique sur le chemin RSABSSA (grep .ecc/elliptic/
basicKey/curve dans util.js et blindrsa.js = vide). Or la faille
GHSA-2w8x-224x-785m est dans sjcl.ecc.basicKey.publicKey (validation point sur
courbe). => Faille HORS PERIMETRE pour notre usage RSA. Le pont crypto peut
etre bati sur blindrsa-ts sans exposition a cette CVE.
PROCHAINE ETAPE (tete reposee) : etape 1 du chantier = test d'interoperabilite
reel. Message aveugle par blindrsa-ts (JS) -> signe par vera_blind_sig (Rust)
-> finalise en JS -> verifie. Attention encodage DER des cles + format des
octets a aligner entre les deux libs.

## Audit couverture de tests (19/07) -- a traiter APRES le refactor crypto
Un audit qualite des tests a identifie des trous. NB : une partie deviendra
caduque avec le refactor crypto (verifier_et_consommer, flux de tokens vont
changer) -- ne pas ecrire ces tests avant le refactor.

Points REELS a garder :
- CONCURRENCE verifier_et_consommer : deux threads consommant le meme token
  -> double vote possible EN THEORIE. Fortement attenue par worker unique
  (impose exprès, GIL + etat memoire), mais a verifier/tester.
- test_signature_production isole la primitive en memoire pure (monkey-patch
  builtins.__import__). Legitime pour la primitive, MAIS manque un test
  d'integration AVEC persistance (round-trip persister->recharge->verifier),
  et le rechargement de cle RSA chiffree + timer de destruction 48h ne sont
  pas testes.
- test_admin_auth : pas de test d'expiration de session (mock time.time()),
  pas de test de timing (compte existant vs inexistant), pas de concurrence.
- test_persistance : pas de test de corruption SQLite, pas de test WAL, pas de
  test d'atomicite de persister_publication_atomique (interruption entre
  ecritures).
- test_precision_kmin : tolerances larges (deja note #8), N_SIM=3000 -> monter
  a 10000, ajouter test de biais (moyenne erreurs ~0) et de forme (KS/chi2).
- Point mineur : test 7 admin_auth (sel) trivialement vrai par construction ;
  test 3 signature ne verifie pas que le rejet est pour la BONNE raison
  (verifier type SignatureInvalideError + message).

Priorite quand on y viendra : concurrence verifier_et_consommer, puis test
d'integration signature+persistance. Le reste est du durcissement progressif.

## Chantier crypto -- 3 exigences de conception (audit Fable 5, 19/07)
Le modele en deux temps (jeton d'autorisation identifiant + signature aveugle
anonyme) est correct (Chaum 1982, Privacy Pass, RSA-BSSA) MAIS n'est validable
qu'avec ces trois parades. A integrer DES la conception de l'endpoint, pas apres.

### EXIGENCE 1 (CRITIQUE) -- Engagement de cle publique
Sans elle, tout le refactor est decoratif. Attaque : un serveur malveillant
signe chaque votant avec une cle RSA DIFFERENTE. Au depouillement, il teste
quelle cle valide chaque token -> desanonymisation totale, sans casser la
crypto. NB : notre test de faisabilite actuel a DEJA cette faille (le client
lit une cle que le serveur fournit).
PARADE OBLIGATOIRE : la cle publique de l'epoque est PUBLIEE et ENGAGEE AVANT
la distribution des jetons (dans le depot, sur la page de consultation, hash
dans le QR code -- publique et unique). Le client verifie sa signature
finalisee contre CETTE cle engagee, jamais contre une cle que le serveur
renvoie a la volee. => CHANGE LE CONTRAT DE L'API : le client doit connaitre
la cle AVANT de contacter le serveur.

### EXIGENCE 2 -- Ensemble d'anonymat = jetons echanges, pas population
L'unlinkability ne vaut que parmi les gens qui ont EFFECTIVEMENT echange leur
jeton dans l'epoque. 6 demandes sur 300 -> anonymat 1-parmi-6, pas 1-parmi-300.
Meme logique que K_MIN. PARADE : depouiller seulement apres cloture (deja fait
via K_MIN) ; DOCUMENTER honnetement que l'ensemble d'anonymat = nombre de
jetons echanges. A resoudre par la doc, pas par la crypto.

### EXIGENCE 3 -- Corrélation par metadonnees reseau (IP)
Demande de signature et vote de la meme IP -> un serveur qui logge les IP
relie les deux, aveuglement ou pas. Meme classe que la limite "observateur
reseau" actuelle. L'unlinkability crypto protege contre ce qui est PERSISTE
(enregistrements), pas contre un serveur qui observe le trafic en direct.
PARADE : Tor, HORS PERIMETRE. A DOCUMENTER dans le threat model, pas a resoudre.

### Deux details d'implementation a ne pas perdre
1. DEUX REGISTRES SEPARES, JAMAIS JOINTS : jeton d'autorisation (Temps 1) et
   hash du token de vote depense (Temps 2) sont deux tables distinctes. Les
   joindre recreerait la liaison.
2. one-token-per-epoch (parade differenciation, porte 7 historique) doit
   SURVIVRE au refactor : un jeton d'autorisation = une epoque = une signature.

Ces trois exigences seront les futures Portes 18 (engagement cle), 19 (ensemble
anonymat), 20 (correlation reseau) une fois le refactor fait et teste.

## Chantier crypto -- DECISION distribution : Option B (19/07)
Question tranchee : comment le votant recoit son acces (lien + jeton d'autorisation).
Trois analyses convergentes (assistant + 2 IA) -> OPTION B.

OPTION B RETENUE : le RH envoie les SMS lui-meme, avec des liens fournis par
VERA. Le serveur ne voit JAMAIS les numeros de telephone.

Pourquoi (raisonnement de fond) : l'autorite d'eligibilite (RH) connait DEJA
l'electorat -- c'est irreductible. L'option A (VERA envoie via passerelle type
Twilio) ne ferait que DUPLIQUER cette connaissance sur le serveur (numeros +
liste + horodatage), elargissant la surface de confiance sans rien apporter.
Donner les numeros au serveur contredit "prouve, pas promis" (on retomberait
sur "le serveur promet de ne pas correler"). B ne donne au RH aucune info
qu'il n'a pas deja.

Risques de A qu'on EVITE en choisissant B :
- Attaque par cle choisie facilitee : un serveur qui controle la distribution
  cible trivialement un individu avec une cle differente -> desanonymisation.
- Correlation temporelle SMS envoye a t / connexion a t+d.
- Twilio = sous-traitant US, PII, RGPD (VERA deviendrait responsable de
  traitement) -- contresens pour un outil dont l'argument est l'anonymat.
- Inference de non-participation : le serveur apprend qui n'a PAS clique.

DEUX CONDITIONS NON NEGOCIABLES pour que B tienne :
1. LE LIEN = CREDENTIAL D'EMISSION UNIQUEMENT. Le lien autorise l'appareil du
   votant a DEMANDER une signature aveugle. Il ne doit JAMAIS contenir le token
   de vote lui-meme. Sinon le RH pourrait relier les votes ou voter a la place
   des abstentionnistes -- FATAL. L'aveuglement se fait cote client, le token
   devoile au vote n'a aucun rapport observable avec le lien.
2. CLE DE SIGNATURE UNIQUE PUBLIEE + verification d'empreinte cote client
   (= Exigence 1 / engagement de cle). Sans elle, l'attaque par cle choisie
   annule tout le benefice de BSSA. Via SMS : hash de la cle dans le fragment
   du lien (#k=HASH), jamais envoye au serveur -> il ne peut pas s'adapter.

RISQUES RESIDUELS DE B a ASSUMER honnetement dans le threat model :
- Bourrage par RH : le serveur ne peut pas verifier que le RH a distribue aux
  vraies personnes. Mitigation : publier le nombre de credentials emis vs
  effectif annonce (les votants constatent). Residu = confiance procedurale.
- Fichier de liaison nom<->lien cote RH (Excel qui traine) : base de liaison
  persistante. Consigne de suppression apres distribution = "promis pas prouve".
- Collusion RH+serveur : ensemble ils savent "P a demande un token a t"
  (participation phase emission), PAS le contenu du vote.
- Coercition douce (RH demande "tu as utilise ton lien ?") : inherent au
  contexte workplace, pas au canal.

## Robustesse : code HTTP sur message aveugle invalide (brique 2)
L'endpoint /api/signer_aveugle renvoie 500 (erreur serveur) quand message_aveugle_hex
n'est pas un message RSABSSA valide (ex: 'deadbeef'). Devrait renvoyer 400/422 (erreur
client). Le jeton est bien consomme (fail-closed correct), seul le code HTTP est faux.
Pas une faille de securite, defaut de robustesse. A corriger apres le refactor crypto.

## Session 21/07 -- points en suspens

### Fix effacement jetons_autorisation (EN COURS, a committer)
effacer_etat_consultation() ne vidait pas la table jetons_autorisation (registre
1). Trace residuelle apres cloture + rejeu inter-consultation possible. FIX FAIT
dans vera_persistance.py (table ajoutee a la boucle + docstring alignee). Reste:
lancer test_effacement_jetons.py (ecrit, pas encore lance) sur base isolee, puis
committer. Porte trouvee par un regard Fable 5 / Opus 4.8, verifiee sur le vrai code.

### Fil securite: anti-rejeu jetons depend de la cloture
La protection anti-rejeu des jetons d'autorisation repose entierement sur le fait
que la cloture (effacer_etat_consultation) a lieu. Un jeton NON consomme, entre
deux consultations sans cloture explicite (redemarrage, reouverture via
ouvrir_consultation), resterait valide. A reprendre dans la brique 7 (Modele B),
quand /api/repondre sera reecrit.

### README Porte 7 perime
Le README decrit Porte 7 comme "partielle, unlinkability pas effective" alors que
le refactor serveur Modele B (couches 1-4) l'a resolue cote serveur. Mettre a jour
Porte 7 + threat model quand le Modele B sera boucle (briques client 5b/6/7
incluses). Formulation juste: "en cours de fermeture, cote serveur fait, client a finir".

### Remote git en token-dans-URL
Le remote origin utilise https://taha-vera:TOKEN@github.com/... Ce format a expose
le token le 21/07 (affiche par git filter-repo). Migrer vers SSH (cle deja utilisee
pour se connecter au serveur) pour ne plus jamais avoir le token dans une URL.

## Dechiffrement des cles RSA : echec silencieux sur passphrase erronee

Constat (session 2026-07-22) : dans `charger_cles_rsa` (vera_persistance.py),
un echec de dechiffrement Fernet est traite par `continue` silencieux. Si
VERA_DB_KEY est erronee au redemarrage (typo dans le unit systemd, restauration
sur une autre machine), les cles existantes sont ignorees sans erreur et de
nouvelles cles sont generees : tous les liens deja distribues (empreinte #k=
dans les SMS) deviennent invalides en pleine consultation, sans aucun signal
cote operateur. C'est la variante silencieuse du probleme historique de cycle
de vie RSA.

Correction envisagee : si la table cle_rsa_active contient des lignes mais
qu'AUCUNE ne se dechiffre, refuser de demarrer (fail-closed, coherent avec le
comportement VERA_DB_KEY absente) plutot que de regenerer. A minima, log
CRITICAL par cle ignoree. Le cas legitime de rotation volontaire passe par la
cloture de consultation, qui purge ces lignes.

Non bloquant : en production la passphrase est fixe dans le unit file, et le
crash test (chantier_crypto/test_crash.mjs) prouve le rechargement correct a
passphrase identique. Le risque ne se materialise que sur erreur operateur.
