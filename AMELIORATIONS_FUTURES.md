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