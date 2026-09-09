# Journal des audits externes de VERA

Ce fichier a ete separe de LIMITS.md le 09/09/2026, pour la seule raison de sa
taille : il en representait 30 ko sur 120, sous un titre qu'aucune table des
matieres de LIMITS.md n'annoncait avant le 07/09.

**Ce que ce document est.** Le recit de ce que quatorze audits externes ont
trouve sur ce depot, et comment chaque constat a ete verifie, corrige ou refute
-- souvent en montrant qu'un correctif precedent avait ferme un cas au lieu
d'une classe. C'est la matiere qu'un auditeur exterieur lit pour savoir si ce
projet se corrige ou se defend.

**Ce que ce document n'est pas.** Une liste de limites. Les limites elles-memes,
leur nature (invariant logiciel / condition d'exploitation / regle procedurale
/ limite assumee), et le decompte qui en fait foi restent dans
[LIMITS.md](LIMITS.md), qui reste le document canonique.

---

## 20. Journal des audits — ce qui a ete trouve, et par qui

*Cette section a ete creee le 07/09/2026. Ces recits s'etaient accumules sous
les sections 9 et 12, dont les titres -- « ce que revele le fichier de base au
repos », « les comptes administrateurs ne survivent pas a un redemarrage » --
ne les annoncaient pas. A eux deux, ces chapitres faisaient 47 % du document.*

*Un lecteur qui cherchait la limite sur les comptes administrateurs y trouvait
l'audit de la persistance, la lecture du module Rust, et une faute de frappe qui
detruisait une consultation. Les sections 9 et 12 ne contiennent plus que les
limites qui leur appartiennent.*

**Pourquoi ces recits restent.** Ils ne decrivent pas des limites du systeme mais
la maniere dont elles ont ete trouvees -- et souvent, comment un correctif a
ferme un cas au lieu d'une classe. C'est ce qu'un auditeur exterieur lit pour
savoir si ce projet se corrige ou se defend. Les deplacer, ce n'est pas les
minimiser : c'est cesser de les faire passer pour ce qu'ils ne sont pas.

### « Par an » autorisait le double, et trois documents le disaient

Constat d'un audit externe le 07/09/2026. La regle etait ecrite « pas plus de
quatre consultations **par an** ». Deux imprecisions dans quatre mots.

**« Par an » se lit comme une annee civile** : quatre publications en decembre
et quatre en janvier respectent la lettre tout en portant epsilon a 4,0 en deux
mois, soit une certitude pire-cas de 98 %. La regle porte sur douze mois
**glissants**, et ce document le disait correctement ailleurs -- mais pas dans
son propre encadre « EN CLAIR », ni dans le guide, ni sur la page d'accueil.

**Et « consultations » au lieu de « publications »** : la correction du 04/09,
apres l'exercice d'equipe rouge, n'avait pas ete propagee a ces trois endroits.
Declarer k groupes contenant les memes personnes donne k mesures en un seul
cycle.

Le meme audit a releve que la page affirmait qu'apres cloture « le serveur ne
conserve alors plus rien », alors que la section 9 dit qu'`historique_consultations`
survit. Corrige.

*Son premier constat -- la divergence entre les cinq conditions de la page et
celles de ce document -- etait deja corrige depuis le 04/09, et exactement comme
il le preconisait : c'est la page qui avait raison, et la liste d'ici a ete
rendue homogene. Il decrivait un etat vieux de trois jours. Deux constats sur
trois, et les deux justes ont fait apparaitre deux occurrences de plus que
celles qu'il citait.*

### La correction de la faute de conjugaison etait elle-meme incomplete

Le lot precedent listait quatre occurrences precises citees par l'audit du
08/09. Deux autres survivaient ailleurs dans la meme page -- « le bruit
protégé » (pour « protège »), « qui hébergé elle-meme le serveur » (pour
« héberge »). Trouvees en deployant, par une lecture directe de la page
servie plutot qu'une supposition sur ce qui restait.

Corrigees, avec un balayage systematique du motif plutot qu'une liste
d'occurrences enumerees a la main -- c'est une liste enumeree qui avait
manque ces deux-la la premiere fois.

### Le patch qui corrigeait la garde CI ne la corrigeait pas

Un relecteur a clone le commit `01acffa` -- pas le patch, le commit pousse --
et cherche `with: fetch-depth: 0` comme cle YAML, pas comme texte dans un
commentaire. Elle n'y etait pas. Le correctif du 09/09 (matin) avait deux
ecritures successives sur la meme variable Python (`s.replace(...)` sans
jamais reassigner `s`), la seconde ecrasant la premiere : seul le commentaire
survivait. Le message affichait « fetch-depth branche », le `grep` d'apres
trouvait une ligne, et je l'ai crue bonne sans verifier que c'etait le `with:`
et non le commentaire.

**Plus grave que l'etat d'avant.** Le premier commentaire disait « est requis »
-- un lecteur attentif voyait le manque. Le second affirmait « est pose sur
l'etape ci-dessus » : la CI restait verte, le commentaire attestait, rien
n'etait verifie. C'est le motif exact que ce document traque partout ailleurs,
cette fois dans son propre correctif.

Corrige, et verifie differemment cette fois : en parsant le YAML avec
`yaml.safe_load()` et en lisant `steps[0]['with']['fetch-depth']`, pas en
comptant les occurrences d'une chaine de caracteres.

**Meme releve : la docstring de `charger_toutes_cles_chiffrees` contredisait
son propre code.** Le correctif du fail-closed etendu (09/09, matin) avait
change `if rows and not resultat` en `if rows and echecs` -- une cle sans salt
compte desormais comme un echec -- sans mettre a jour la docstring, qui disait
encore « ignoree avec avertissement plutot que de bloquer », ni le `print` six
lignes avant le `raise`, qui disait encore « ignoree ». Alignes.

**La reference CVE a ete demandee en confirmation** -- l'API GitHub avait
limite le releveur en plein controle. Verifiee via cinq sources independantes
au moment de l'ecrire (GitHub Advisory Database, SentinelOne, GitLab Advisory
Database, une mise a jour Fedora, et le changelog amont pyca/cryptography) :
GHSA-g6cj-pr64-35w5 / CVE-2026-69247, severite CVSS 8.2 (High), Bleichenbacher
sur `pkcs7_decrypt_der/pem/smime`, introduite en 44.0.0, corrigee en 50.0.0.
Reference confirmee, maintenue telle quelle.

### Huit constats, huit confirmes : le meilleur taux de tout le journal

Audit du 09/09/2026, dépôt cloné en entier -- API, persistance, gestionnaire
de signature, auth, DP, budget epsilon, module Rust, `vote.html`, `admin.html`,
conf nginx, workflows CI. Chaque point citait un fichier et une ligne. Les huit
ont ete verifies un par un sur le code reel, et **les huit tenaient** -- le
meilleur taux recu sur ce projet.

**Le plus grave, confirme jusqu'au type d'exception leve par le Rust.** Le
jeton est consomme avant la tentative de signature. Un message aveugle de
mauvaise taille fait lever `PyValueError` cote Rust, devenu `ValueError` en
Python -- capture par AUCUN `except` de l'endpoint, qui n'attrapait que
`RuntimeError`. 500 avec trace interne, jeton deja brule, voix perdue sans
recours. C'est exactement la classe que `/api/repondre` avait fermee ; le
correctif avait ferme ce cas-la, pas la classe. Une validation de longueur
(256 octets, coherente avec la cle RSA 2048 bits) precede desormais la
consommation, et la capture est elargie a `ValueError` en filet de securite.
**Verifie a l'execution** : 256 octets passent, toute autre taille est
refusee en 422 avant que le jeton ne soit touche.

**La garde CI la plus recente etait inerte depuis sa creation.** Le
commentaire de l'etape de balayage de secrets disait "fetch-depth: 0 est
requis" depuis le 04/09 -- sans que ce parametre soit jamais pose sur
`actions/checkout`. La garde tournait sur un seul commit depuis le premier
jour. Corrige.

**Le fail-closed sur les cles ne couvrait que la perte totale.**
`if rows and not resultat` laissait demarrer un dechiffrement partiel -- 4
cles sur 5 suffisaient. Consequence identique au cas total que ce garde-fou
visait deja : `generer_autorisations` fabriquerait une cle neuve pour le
departement perdu, changeant l'empreinte de l'ensemble, invalidant tous les
liens de tous les groupes. Etendu a toute perte. **Verifie a l'execution** :
une seule cle corrompue sur trois bloque desormais le demarrage.

**L'absence de compte admin ne produisait aucune erreur.**
`amorcer_compte_principal()` retourne `None`, documente comme tel, si
`VERA_ADMIN_USER`/`VERA_ADMIN_HASH` sont absents -- et l'appelant ignorait ce
retour. Le service demarrait, acceptait des votes, mais personne ne pouvait
jamais publier ni CLOTURER : l'effacement promis n'aurait jamais lieu. Dans un
module qui refuse de demarrer pour un worker en trop ou une ecoute non-
loopback, c'etait l'incoherence la plus visible. Le retour est desormais
verifie, et son absence leve un refus explicite.

**La redirection HTTP vers HTTPS ne couvrait qu'un nom sur trois.** Un bloc
`if ($host = ...)` genere par Certbot, figé sur l'ancien domaine DuckDNS au
premier reglage, jamais etendu lors de la migration du 02/09 : `.fr` et
`www.` tombaient sur un `return 404` inconditionnel. Etendu aux trois noms.

**La creation de compte RH etait le seul endpoint privilegie sans aucune
protection.** Ni verification applicative, ni bloc nginx dedie -- elle
tombait dans le fourre-tout a 5 r/s quand `/api/rh/connexion` en recoit 1,
avec blocage croissant. Un compte obtenu donne publication, cloture (donc
effacement) et generation d'autorisations. Reutilise le meme mecanisme anti-
force-brute, ajoute un bloc nginx au meme niveau, documente
`VERA_SECRET_CREATION_COMPTE` -- absente du README jusqu'ici -- avec une
recommandation d'entropie.

**`admin.html` avait un point d'injection non exploitable, mais implicite.**
`${r.lien_sms}` et `${ligneEcheance}` s'inseraient bruts dans `innerHTML`,
seuls du fichier a ne pas passer par `echapperHtml`. Non exploitable
aujourd'hui -- le jeton vient de `token_urlsafe`, le nom de groupe est deja
contraint cote serveur -- mais c'etait une dependance implicite a un encodage
distant. Echappe.

**Quatre points mineurs, tous confirmes.** `/static/vote.html` etait le seul
bloc du parcours de vote sans `limit_req`, alors que `/vote` -- qui sert la
meme page -- en porte un. Quatre imports morts retires : `Header` (fastapi,
jamais utilise), `appliquer_bruit_dp` (jamais appele, seulement cite dans un
commentaire), et deux symboles + deux exceptions de `vera_signature_manager`
appartenant au Modele A (jeton signe cote serveur), remplace par le Modele B
depuis longtemps. Et `cryptography==49.0.0` portait CVE-2026-69247
(GHSA-g6cj-pr64-35w5, 8.2/High, Bleichenbacher sur le dechiffrement PKCS#7) --
verifie que VERA n'appelle aucune des trois fonctions concernees (seuls
`Fernet` et `PBKDF2HMAC` sont utilises, non affectes), mis a jour vers 50.0.0
quand meme : un scanner automatise la signale independamment de l'usage reel.

### La page d'accueil portait une faute de conjugaison

Constat d'un audit externe le 08/09/2026, sur les deux copies servies -- la
vitrine github.io et vera-consultation.fr. Quatre phrases disaient « celui qui
hébergé n'a pas la liste », « le bruit differentiel protégé chaque
participant » : un accent au mauvais endroit avait transforme un verbe au
present (« héberge », « protège ») en participe passe (« hébergé »,
« protégé ») -- une passe de correction d'accents anterieure avait mal
conjugue plutot que mal accentue.

Sur une page dont l'argument entier est la rigueur, une faute de grammaire
dans la phrase qui explique la separation des roles est ce qu'un DSI ou un
DPO remarque en premier. Corrige, avec le reste des mots signales par le
meme audit : mathematique, separation, decompte, bibliotheque, redhibitoire,
et deux occurrences de « Modele de menace » restees sans accent dans les
liens du pied de page.

Ses trois autres constats decrivaient un etat deja corrige : la licence MIT
du README (corrigee le 23/08), la contradiction « verifie en conditions
reelles » (la phrase incriminee ne contient plus cette formule depuis le
05/09), et la table de divergences taux/invites/precision/contact/version
entre le site et le README (alignee depuis plusieurs jours). Verifie plutot
que suppose.

Son point sur la racine surchargee -- modules serveur, tests et fichiers du
site au meme niveau -- reste juste, et il note lui-meme la raison de ne pas
le faire aujourd'hui : les chemins sont lus par `VERIFICATION_CLIENT.md`, et
un tel deplacement doit se faire en un seul commit tague, pas au fil de
l'eau.

### L'adresse de signalement etait une boite personnelle

Deux auditeurs l'ont releve, en notant que la correction couterait cinq minutes
pour un effet disproportionne sur la perception. Un chercheur en securite qui
lit `SECURITY.md` et y trouve une adresse Hotmail en tire une conclusion sur le
serieux du dispositif, avant meme d'avoir lu une ligne de code.

`securite@vera-consultation.fr` depuis le 07/09/2026, sur le domaine du projet.
Ce n'est pas une redirection mais une boite : les reponses partent donc du meme
domaine que celui qui recoit, ce qui evite qu'un echange sur une vulnerabilite
change d'adresse en cours de route.

L'ancienne adresse est retiree de `SECURITY.md`, du README, du modele de menace
et de la vitrine. Elle subsiste dans `docs/archive/`, datee comme le reste de ce
document. Une garde interdit qu'elle reapparaisse ailleurs.

*En ecrivant cette garde, une incoherence interne est apparue : la liste des
marqueurs qui excusent une citation datee ne contenait ni « etait » ni
« jusqu'au », alors que l'autre controle du meme fichier les accepte depuis
toujours. Deux listes pour la meme notion, et elles avaient diverge. Alignees.*

### « Base chiffree » promettait plus que le code ne fait

Constat d'un audit externe le 04/09/2026. `VERA_DB_KEY` etait decrite comme la
« cle de chiffrement de la base », et le module de persistance comme
« persistance chiffree de l'etat ». En realite, Fernet n'est appele que par les
trois fonctions de `cle_rsa_active` : **seule la cle privee RSA est chiffree au
repos.**

Les autres tables sont en clair. Ce n'est pas un oubli -- elles ne contiennent
aucune donnee en clair : empreintes SHA-256 des jetons, empreintes SHA-384 des
secrets, compteurs agreges destines a etre publies. Et chiffrer ne protegerait
que contre le vol du fichier, lequel donne deja acces a la cle, qui vit dans
l'environnement du processus.

**Mais un DPO qui lit « base chiffree » conclut qu'un instantane d'hyperviseur
est inoffensif. Il ne l'est pas** : il revele qui a participe, par les
empreintes de jetons que l'organisation detentrice de la liste peut recalculer.
C'est la cinquieme trace de participation decrite en section 1.

Formulation corrigee partout. Pour chiffrer le volume entier, c'est LUKS, au
niveau systeme -- hors perimetre, comme pour l'effacement forensique.

### La compression aurait defait tout le bourrage

`gzip` n'etait jamais coupe dans la configuration nginx. Les octets de
remplissage sont des « x » repetes : mesure faite le 04/09, **971 octets
constants tombent a 85 pour « RH » et 105 pour « Securite generale »**. L'ecart
entre services redevient lisible, et le bourrage -- corrige au prix de deux
passes en aout -- ne sert plus a rien.

Cela tenait pour une raison fragile : la configuration Ubuntu par defaut ne
compresse que `text/html`. Le jour ou quelqu'un ajoute `gzip_types
application/json`, la protection tombe **sans qu'aucun test ne le voie**. Meme
motif que les journaux uvicorn : une protection qui repose sur un defaut
d'environnement n'en est pas une.

`gzip off;` est desormais explicite, et `tests/test_bourrage_client_serveur.py`
echoue si la compression revient ou si la ligne disparait.

### Le blocage par compte enfermait son proprietaire dehors

Le compteur par compte ajoute le matin meme -- pour contrer une attaque
distribuee -- etait verifie AVANT le mot de passe, afin de ne pas payer le
PBKDF2 sur une tentative condamnee. Le meme audit a montre l'effet : qui connait
l'identifiant RH le maintient bloque en permanence a 1,4 tentative par minute.
Sur sept jours, l'organisateur perd son tableau de bord et surtout
`POST /api/rh/cloturer` -- **l'effacement promis aux participants**.

Un blocage qui empeche la cloture est pire que la force brute qu'il arrete.

Les identifiants sont desormais verifies d'abord : les bons passent, blocage ou
non ; le blocage ne s'applique qu'a un echec. L'amplification ne rouvre pas pour
autant -- nginx limite cette route a 1 r/s par adresse, soit au pire 10 % d'un
coeur, et le blocage par IP reste la premiere ligne.

*Au passage : `hmac.compare_digest` recevait deux `str`. Il leve `TypeError` sur
un caractere non-ASCII -- un secret d'administration accentue produisait un 500
au lieu d'un 403. Compare en octets desormais.*

### Nginx etait contournable sans que rien ne le verifie

Toute la protection reseau vit dans nginx : `access_log off` sur les routes de
vote, `error_log crit` pour que la limitation de debit n'y reinscrive pas les
adresses, les en-tetes CSP, la limitation elle-meme. Si uvicorn ecoutait sur
`0.0.0.0`, un client atteignant directement le port **contournerait la totalite
de cette couche**.

Rien ne l'empechait. Un audit externe l'a qualifie le 04/09/2026 de « lecon de
la Porte 19 appliquee a moitie » -- une protection qui repose sur une hypothese
d'environnement que rien ne verifie. La formule est juste, et c'est exactement
le motif que ce document poursuit.

Le service refuse desormais de demarrer si `--host` designe autre chose que la
boucle locale, sur le modele de la garde worker unique : inspection de
`sys.argv`, pas de supposition. `VERA_ECOUTE_PUBLIQUE=1` permet de passer outre
en developpement -- il faut la poser volontairement, ce qui distingue un choix
d'un oubli.

*Deux durcissements de la CI au passage : `opendp` est epingle sur la version de
production (les portes 2 et 3 etaient validees sur une version quelconque), et
le workflow declare `permissions: contents: read` -- il ne fait que lire, un
jeton en ecriture n'a aucune raison d'y exister.*

### L'historique complet balaye : aucun secret

La garde `test_repli_admin_retire.py` verifie l'arbre de travail. Un audit
externe a note le 04/09/2026 qu'elle ne dit rien des commits passes -- remarque
pertinente sur ce projet precisement, puisque des secrets y ont reellement fuite
le 31/07/2026, par le mot de passe en clair dans l'unite systemd. **Un secret
retire d'un fichier reste dans l'historique**, et un depot public le rend
consultable indefiniment.

Les **525 commits** ont ete balayes. Resultat : aucun secret. Cinq occurrences
de `VERA_ADMIN_PASS`, toutes des constantes de test explicites --
`mdp_de_test`, `motdepasse_de_test`, `CONSTANTE_DE_TEST_PAS_UN_SECRET`,
`test1234` -- plus la ligne d'extraction depuis l'unite systemd, corrigee le
23/08. Aucune cle privee. Aucun fichier `.db`, `.env`, `.key` ou `.pem` n'a
jamais ete versionne. Les seules chaines de haute entropie sont les empreintes
publiees de la page de vote, dont c'est la raison d'etre.

**La fuite du 31/07 n'est donc jamais passee par git** : elle a eu lieu dans
l'unite systemd du serveur, qui n'est pas versionnee. C'est coherent avec ce que
la section 12 en dit, et cela vaut d'etre etabli plutot que suppose.

Le balayage tourne desormais a chaque poussee (`.github/workflows/gardes.yml`),
sur l'historique complet -- `fetch-depth: 0`, sans quoi il ne verrait qu'un
commit.

### `unsafe-inline` etait le cran ouvert du scenario « operateur actif »

Constat d'un audit externe le 04/09/2026. La section 6 pose le scenario de
l'operateur qui sert un JavaScript modifie, et conclut qu'aucune verification
executee dans un navigateur n'en protege. La CSP autorisait `'unsafe-inline'`
sur `script-src` : n'importe quel script injecte dans une page s'executait.

L'auditeur notait a juste titre que la fermeture etait bon marche -- les pages
sont statiques, et leurs empreintes sont deja publiees. `script-src` porte
desormais les empreintes des deux scripts inline du projet. Un troisieme, ou une
modification de l'un des deux, ne s'executerait pas.

**Cela ne ferme pas la section 6**, et il ne faut pas le laisser croire : un
operateur qui sert la page sert aussi l'en-tete qui la contraint. Ce qui est
ferme, c'est l'injection par un tiers -- une faille de la page elle-meme, un
intermediaire reseau. C'est un cran, pas la porte.

**Et le correctif cree un couplage qu'il faut garder.** Modifier une ligne du
script inline de `vote.html` sans mettre a jour la configuration nginx rend la
page SILENCIEUSEMENT inerte : le navigateur bloque le script, le votant voit une
page qui ne repond pas, et rien ne l'explique. C'est la desynchronisation
manuelle que ce document traque ailleurs.

`tests/test_empreintes_publiees.py` recalcule ces empreintes a chaque passage et
echoue dans les trois sens : `unsafe-inline` retabli, script modifie sans la
conf, empreinte de la conf ne correspondant a aucun script.

*`style-src` garde `'unsafe-inline'` : les pages utilisent des attributs
`style="..."` que les empreintes CSP ne couvrent pas. Un style injecte
n'execute pas de code -- le gain serait cosmetique, le cout reel.*

### Le verrouillage anti-force brute ne ralentissait jamais

Constat d'un audit externe le 04/09/2026. Cinq echecs declenchaient un blocage
de cinq minutes, puis le compteur repassait a zero : en regime permanent, une
adresse obtenait **60 tentatives par heure, indefiniment et sans jamais
ralentir**. Sans compteur par compte, l'attaque se distribuait sur plusieurs
adresses sans rien couter.

**Et c'etait aussi un amplificateur de deni de service.** Chaque tentative
declenche un PBKDF2 a 200 000 iterations -- environ 100 ms -- sur un service
mono-processus, celui-la meme qui sert les votants. Occuper le seul worker
n'exigeait pas de trouver le mot de passe.

Deux corrections. Le blocage **double a chaque recidive**, jusqu'a une heure :
quarante tentatives coutent desormais 315 minutes d'attente cumulee contre 40
auparavant. Et un **compteur par compte** suit l'identifiant vise quelle que
soit la provenance -- verifie AVANT le PBKDF2, ce qui coupe l'amplification a la
racine.

*En ecrivant ce second compteur, un defaut a ete introduit puis corrige : sa cle
est l'identifiant ESSAYE, que l'attaquant choisit. Sans purge, un million
d'identifiants distincts auraient fait croitre le dictionnaire indefiniment --
une fuite memoire a la place d'une amplification CPU. La purge suit la meme
regle que celle des adresses : liberer seulement si le blocage est expire ET
l'entree inactive.*

### Un resultat faux pouvait etre publie sans bruit

Constat d'un audit externe le 04/09/2026, et le plus serieux de son lot.
`_projeter_sur_simplexe` bouclait cent fois puis sortait **sans verifier qu'elle
avait converge**. Et sa correction d'arrondi, `max(0, entiers[i_max] + delta)`,
pouvait casser l'invariant de somme qu'elle venait de retablir.

Aucune fuite : tout ceci est du post-traitement, gratuit en epsilon. Mais un
vecteur hors du simplexe -- somme differente de l'effectif, ou case negative --
aurait ete publie sans que rien ne le signale. **Un resultat faux publie en
silence, c'est exactement ce que ce projet refuse partout ailleurs.**

Deux fail-closed ajoutes : la non-convergence leve, et le contrat de la fonction
est verifie avant de rendre. Mesure sur 20 000 projections a quatre effectifs,
cas extremes compris : aucun declenchement. La garde ne crie pas au loup.

**Et « garantie DP calculee par OpenDP » surpromettait.** Le code appelle
`enable_features("contrib")` -- composants qu'OpenDP declare explicitement non
vettes -- et la bibliotheque ne fournit que l'echantillonneur Laplace SCALAIRE.
La comptabilite du vecteur a trois cases est un raisonnement de ce projet,
demontre en section 14. La page d'accueil dit desormais « bruit echantillonne
par OpenDP, comptabilite demontree dans les limites ».

### Le document le plus lu etait le moins controle

Constat d'un audit externe le 04/09/2026. `test_parametres_documentes.py`
parcourait les `.md`, les `.py` et `static/vote.html` -- **jamais
`index.html`**, qui est la page d'accueil du projet : celle qu'ouvre un DRH ou
un delegue avant tout le reste.

Elle divergeait deja. Sa liste des cinq conditions n'etait pas celle de la
section 0 de ce document. Et c'est `index.html` qui avait raison : la liste
d'ici incluait le seuil de 240 sous une phrase affirmant qu'« aucune n'est tenue
par le code seul », alors que ce seuil est precisement applique par le code --
la grille des quatre natures, ajoutee le 26/08 juste en dessous, le classe en
invariant logiciel. J'avais ajoute la grille sans revoir le texte qu'elle
contredisait.

Corrige dans les deux sens : la liste des cinq conditions est desormais
homogene -- toutes hors du code, la regle des 4 publications / 12 mois y prenant
la place du seuil -- et la garde parcourt les pages HTML.

**Un faux positif est apparu en l'etendant**, et il vaut d'etre note : la balise
`viewport` de chaque page fixe une echelle initiale de 1, que le motif lisait
comme une declaration du parametre SCALE -- lequel vaut 4 dans le code. Il
utilisait `\b`, qui ne coupe pas apres un tiret. Il exige desormais que le caractere precedent ne soit ni lettre ni tiret.
Le motif etait tolerable tant que la garde ne voyait que du Markdown et du
Python -- etendre une garde, c'est aussi decouvrir ce qu'elle tolerait.

### Quatre propositions refusees, et pourquoi

Un audit du 03/09/2026 a formule des recommandations qui, appliquees,
detruiraient ce qu'elles cherchent a proteger. Elles sont consignees ici parce
qu'elles reviendront : elles sont raisonnables pour un systeme ordinaire, et
fausses pour celui-ci.

**« Ajouter des empreintes des membres des groupes dans
`historique_consultations` pour empecher le contournement par renommage. »**
Refuse, et c'est la plus grave des quatre. VERA ne connait pas vos membres --
c'est la moitie de la separation des roles. Stocker leurs empreintes exigerait
que l'organisation transmette sa liste au serveur : celui-ci detiendrait alors
la liste ET la base, soit exactement la configuration que tout le dispositif
interdit. On fermerait un avertissement de bonne foi en ouvrant la
desanonymisation complete. Le contournement par renommage reste, et reste
documente ; le controle en revient au representant du personnel, a qui le guide
indique desormais quoi regarder.

**« Utiliser un cache partage, type Redis, pour permettre plusieurs workers. »**
Refuse. Ce cache contient le couple (empreinte du jeton, empreinte du message
aveugle). Le placer dans un service reseau, c'est le sortir de la memoire du
processus -- il devient persistable, observable, sauvegardable. Le choix de la
memoire n'est pas une limite technique a lever, c'est la mesure de protection.

**« Journaliser les evenements de haut niveau pour la responsabilite. »**
Refuse en l'etat. Les journaux sont precisement ce que ce projet a passe des
semaines a couper : `access_log off` sur les routes de vote, `error_log crit`
pour que la limitation de debit n'y reinscrive pas les adresses IP. Un journal
d'audit qui note « consultation ouverte a 14h02 » est sans danger ; la frontiere
avec « jeton consomme a 14h02:47 » est mince, et c'est le canal temporel de la
section 9. A ne rouvrir qu'avec une regle explicite sur ce qui peut y figurer.

**« Verifier l'atomicite avec EXPLAIN QUERY PLAN. »** Refuse : cet outil montre
comment SQLite execute une requete -- index utilises, ordre de parcours. Il ne
dit rien des frontieres de transaction. L'atomicite se verifie en tuant le
processus entre deux ecritures, ce que fait `tests/test_atomicite_publication.py`.

**Une seule est retenue, et elle etait deja notee** : ecraser la memoire du cache
avec des `bytearray` plutot que de compter sur `del`. Le module le dit lui-meme
depuis le 26/08 -- « envisageable, non fait a ce jour ». Le gain est reel mais
etroit : il ne protege que contre un vidage de memoire pris dans la fenetre
d'une heure, et Python ne garantit de toute facon pas l'absence de copies
intermediaires.

**Une cloture interrompue laissait la base dans un etat que rien ne
signalait.** La cloture enchaine plusieurs effacements -- cles RSA, etat de
consultation, cache memoire. Si le processus meurt au milieu (coupure, OOM,
redemarrage force), il reste une base sans consultation active mais avec des
jetons ou des empreintes de votes.

Ce qui subsiste alors n'est pas anodin : `jetons_autorisation` porte la
cinquieme trace de participation decrite plus haut, celle qu'une organisation
detenant la liste peut lire directement. Elle etait censee disparaitre.

Le service le RAPPORTE desormais au demarrage, sans corriger : effacer
automatiquement detruirait une consultation en cours si le diagnostic se
trompait, et ce serait irrattrapable. Propose par un audit externe le
03/09/2026.

*Le meme audit recommandait de verifier que `effacer_cle_rsa()` suit bien
`effacer_etat_consultation()`. C'est le cas : `fermer_consultation()` appelle
les deux, et l'API l'invoque avant l'effacement de l'etat.*

**L'effacement de cloture est verifie sur les OCTETS depuis le 03/09/2026.**
Douze audits avaient lu le code et approuve le raisonnement -- `secure_delete`,
les `DELETE`, le `VACUUM` -- sans jamais ouvrir le fichier apres coup.
`tests/test_effacement_forensique.py` monte une consultation complete, releve
les empreintes de jetons, les empreintes de secrets et l'intitule de la
question, verifie qu'ils sont bien dans le fichier AVANT (sans quoi le test ne
prouverait rien), cloture, puis relit les octets.

**Ils ont disparu.** La Porte 14 tient au niveau ou elle est affirmee.

**Et la mesure a montre autre chose : les deux mecanismes sont redondants.**
Sans `secure_delete` ET sans `VACUUM`, les onze valeurs subsistent. Avec l'un OU
l'autre, elles disparaissent. C'est une bonne propriete -- une modification
involontaire de l'un ne rouvre pas la porte -- mais le commentaire du code
laissait croire que chacun etait necessaire. Il decrit desormais ce qui est
mesure.

Ce test etablit une minimisation APPLICATIVE, pas une destruction forensique du
support : il ne dit rien du nivellement d'usure des SSD, des instantanes
d'hyperviseur, des sauvegardes ni du fichier d'echange. Voir plus haut.

**La cloture est visible dans les entrees-sorties du serveur.** `VACUUM`
reecrit integralement le fichier : qui observe le systeme -- pas la base, le
systeme -- voit une operation d'ecriture massive a un instant precis, et en
deduit qu'une consultation vient d'etre close. Releve le 03/09/2026.

Ce n'est pas une fuite de reponse, et l'instant de cloture n'est pas un secret :
il est annonce aux participants, et le resultat est publie. Mais c'est une
metadonnee que ce document ne listait pas, et elle appartient a la meme famille
que les canaux de la section 9 -- observable par l'hebergeur, pas par
l'organisation qui consulte.

**Ce que `journal_mode=DELETE` ne fait pas.** SQLite ecrit toujours un journal de
rollback PENDANT une transaction d'ecriture, et le supprime au commit. Un
observateur capable de lire le fichier a cet instant precis -- ou d'observer les
metadonnees du systeme de fichiers -- peut donc encore voir passer une ecriture.
Le passage au mode DELETE fait passer la fenetre de PERMANENTE a quelques
millisecondes, et exige desormais une lecture SYNCHRONE plutot qu'un instantane
pris apres coup ; il ne la supprime pas.

Cette nuance ne change pas le perimetre -- « toute lecture repetee » est deja
hors modele -- mais elle change ce qu'on peut affirmer. Le commentaire du code
disait « DELETE ferme la classe » ; un audit externe l'a releve le 03/09/2026
comme trop fort. Formulation exacte : DELETE empeche le journal de PERSISTER
entre les transactions.

**Deux fonctions de dérivation distinctes, à ne pas confondre.** Les mots de
passe d'administration utilisent PBKDF2-HMAC-SHA256 à **200 000** itérations
(`vera_admin_auth.py`). La clé de chiffrement de la base est dérivée de
`VERA_DB_KEY` par PBKDF2 à **100 000** itérations (`vera_persistance.py`). Deux
usages différents, deux paramètres différents — un document qui cite l'un des
deux sans préciser lequel crée une contradiction apparente.

**Une table survit a la clôture** : `historique_consultations`, qui note le nom
de chaque groupe consulté et la date. Elle sert a l'avertissement de frequence
(section 14) et ne contient ni réponse ni identite -- mais cette section se
voulant exhaustive, elle merite d'y figurer.

Le modèle de menace exclut donc non seulement le vol du fichier, mais **toute
lecture répétée** : sauvegardes incrémentales, réplication, instantanés
d'hyperviseur, agent de supervision lisant `/root`. C'est une condition
d'exploitation, pas une propriété du code — elle doit figurer dans les
engagements pris avec l'hébergeur.

Cette exposition des agrégats en clair est acceptable dans le modèle de menace
retenu : le fichier est déjà protégé par le système d'exploitation et l'accès
SSH, et les compteurs agrégés sont de toute façon destinés à être publiés
(sous forme bruitée). Une organisation dont la simple structure de consultation
serait elle-même sensible devrait chiffrer le volume au niveau système
(LUKS/dm-crypt), ce qui sort du périmètre de VERA.

Vérifié par test_chiffrement_repos.py.

### Une faute de frappe pouvait detruire une consultation entiere

Constat d'un audit externe le 03/09/2026. C'est le defaut le plus couteux trouve
sur ce projet -- il ne casse pas l'anonymat, il rend la consultation
irrecuperable.

`/api/rh/generer_autorisations` appelait `cle_publique(groupe)` AVANT de verifier
que le groupe figurait dans la liste declaree. Cette methode est CREATRICE si la
cle est absente, et elle la persiste. Le refus arrivait donc apres coup :
l'empreinte de l'ENSEMBLE des cles -- celle inscrite dans chaque lien deja
distribue -- avait change.

« Ateliers » pour « Atelier », une majuscule, un pluriel : le motif de validation
du champ accepte tout nom bien forme, il ne verifie aucune appartenance. Le RH
voyait un message d'erreur clair et croyait qu'il ne s'etait rien passe. **Tous
les votants, tous groupes confondus**, recevaient ensuite « la configuration du
serveur ne correspond pas a ce lien. Vote refuse par securite ».

Et l'etat etait irrecuperable : aucune route ne retire une cle, seule la cloture
les detruit toutes. Il fallait recommencer la consultation et redistribuer les
liens.

Le commentaire du code decrivait exactement ce defaut -- il expliquait pourquoi
le controle existe. **Il ne disait pas qu'il s'executait trop tard.** L'ordre est
corrige, et `tests/test_ordre_creation_cle.py` echoue si on l'inverse, si un
refus passe apres la creation, ou si un endpoint public appelle la variante
creatrice.

**Et l'outil du tiers plantait encore.** La garde du 29/08 protegeait
`calculer_agregat`, ou le defaut etait apparu. Elle ne protegeait pas la ligne
qui lit `departement` cent lignes plus haut : un serveur omettant ce champ
faisait toujours planter l'outil. Le correctif avait ferme le point, pas la
classe. La forme de la reponse est desormais validee une fois, avant tout
traitement.

### Ce que le representant du personnel pouvait reellement faire : rien

Quatre constats du meme audit, le 03/09/2026, tous sur la seule verification que
ce document confie a un non-technicien.

**Le guide ne nommait pas l'outil prevu pour lui.** Il renvoyait le delegue vers
`/api/engagement_cles` -- du JSON contenant des cles publiques en hexadecimal.
`verifier_engagement.py` existe, affiche les chiffres en clair et signale les
anomalies, mais n'etait cite que dans deux documents techniques que le guide ne
demande pas de transmettre. Zero occurrence dans le guide.

**L'option `--groupes` n'etait jamais comparee, sans le dire.** Le correctif du
29/08 avait protege `--attendu` ; `--groupes`, declare sur la ligne d'a cote,
restait muet. Le delegue fournissait sa liste de reference, elle n'etait pas
regardee, et il obtenait un code 0. **Reponse litterale a la question posee :
non, il ne savait pas distinguer « rien a signaler » de « le controle n'a pas eu
lieu ».** Les arguments de comparaison sont desormais traites ensemble.

**Deux listes de cinq, avec la meme formule d'autorite.** Ce document enonce
cinq CONDITIONS -- 240 reponses, hebergement tiers, attestation d'effectif,
groupes disjoints, transporteur independant. Le guide enonce cinq TACHES --
liste des invites, destruction de cette liste, information RGPD, decoupage,
choix du transporteur. Rien ne les distinguait.

L'ecart de fond porte sur **l'hebergement par un tiers** : non optionnel ici,
presente dans le guide comme une question a trancher avec le DPO, l'auto-
hebergement y apparaissant comme une option degradee mais praticable. Un delegue
qui n'ouvrait que le guide ne savait pas qu'il devait l'exiger. Le guide renvoie
desormais ici et dit lequel des deux fait foi.

**Et le format du lien etait mal documente dans le code.** La docstring de
`/vote` annoncait le jeton en query string ; il vit dans le fragment, ce qui
l'empeche d'atteindre un journal d'acces. Un lien conforme a cette description
aurait affiche « Lien incomplet » -- et aurait fait passer le jeton par le
serveur.

### Six faiblesses du meme audit, dont deux qui detruisent la confiance

**Une empreinte correcte en majuscules etait declaree compromission.** La
comparaison etait `recalcule != args.attendu.strip()` : `hexdigest()` rend des
minuscules, et `strip()` ne retire que les blancs de bord. Une empreinte juste,
recopiee depuis un proces-verbal avec une majuscule ou un espace au milieu,
declenchait « ANOMALIE GRAVE -- le jeu de cles a change ».

Le cout n'est pas l'erreur : c'est ce qu'elle produit. Soit le delegue suspend
une consultation saine, soit -- plus probable apres une premiere fausse alerte --
il cesse de croire l'outil. **Un controle qui crie au loup ne protege plus
personne.** La comparaison normalise desormais casse et espaces.

**« Aucune consultation ouverte » se lisait comme un feu vert.** Le message etait
exact, mais quelqu'un qui vient de « faire la verification » y lisait une
validation. Un controle lance avant la declaration des groupes, ou apres la
cloture, comptait comme un controle reussi. Le script dit maintenant que ce n'en
est pas un, et quand relancer.

**Un tri divergent pouvait detruire une consultation.** Le serveur trie par point
de code, le client en unites UTF-16. Les deux ordres coincident partout sauf
au-dela de U+FFFF : deux groupes nommes « ﬁn » et « 𝐀telier » -- tous deux
acceptes, `\w` admettant les lettres mathematiques -- produisaient deux agregats
differents, donc TOUS les votes refuses. L'auditeur l'avait signale sans le
confirmer ; reproduit le 03/09. Les caracteres hors BMP sont refuses a la source,
plutot que d'entretenir l'egalite de deux tris dans deux langages.

**Trois constats plus legers.** L'affirmation que le marqueur de participation
est « la seule trace qui survit sur l'appareil » ignorait le `sessionStorage`,
qui garde la reponse jusqu'au succes du depot -- corrigee ici meme. La page de
vote etait accessible sous un second chemin, `/static/vote.html`, sans bloc de
non-journalisation. Et la configuration nginx publiee annoncait encore le seul
domaine DuckDNS, ce qui contredisait la procedure de verification.

### La phrase la plus absolue du projet etait celle que lit le votant

Le meme audit, le 03/09/2026, en la donnant comme son constat le moins assure --
« cela releve du jugement, pas de la verification ». Il avait raison sur les deux
points : c'est un jugement, et il est juste.

La page de vote conseillait de repondre depuis un telephone personnel, et
ajoutait : « **Votre reponse est protegee dans tous les cas**, mais un appareil
professionnel peut garder la trace que vous avez participe ».

Deux choses n'allaient pas. La formule est categorique -- « dans tous les cas » --
sur un systeme dont le README dit desormais « aucune partie legitime, prise
isolement », et dont la section 9 du present document enumere les canaux
temporels qui ne sont pas couverts. **La phrase la plus absolue du projet etait
celle adressee a la personne qu'il s'agit de proteger.**

Et elle etait mal placee : elle servait a rassurer sur l'usage d'un appareil
professionnel, c'est-a-dire dans le cas ou la protection est la plus faible.

Remplacee par ce qui est vrai et suffisant : « ce que vous repondez ne part
jamais avec votre nom ; en revanche, un appareil ou un reseau professionnel peut
garder la trace que vous avez participe ». Le votant a besoin de savoir ce qui
est protege et ce qui ne l'est pas, pas d'etre rassure.

### `vera_persistance.py`, 980 lignes, enfin auditees

Un auditeur l'avait nommee comme non auditee ; c'est fait le 03/09/2026. Quatre
constats, deux qui tiennent et deux dont la portee etait surevaluee.

**Le delai de connexion SQLite n'etait pas fixe** : le module prenait la valeur
par defaut de la distribution -- cinq secondes le plus souvent, mais rien ne le
garantit. Un verrou pose par une sauvegarde ou un agent de supervision faisait
echouer une transaction en `OperationalError`, sans aucune reprise : le vote
etait perdu. Porte a trente secondes, explicitement.

**`initialiser()` n'etait pas idempotente** : un second appel remplacait la
connexion sans fermer l'ancienne -- fuite de descripteur, verrous SQLite
conserves par la connexion orpheline. Le cas ne survient pas en exploitation
normale, mais un module de persistance ne doit pas dependre de la discipline de
son appelant. Garde ajoutee.

**Deux constats dont la portee etait surevaluee**, et il vaut de dire pourquoi.

Le `VACUUM` sous verrou global etait qualifie de « deni de service par
construction ». La mecanique est exacte -- la reecriture du fichier bloque tout
-- mais cette fonction n'est appelee que par la CLOTURE : la consultation est
alors fermee, plus aucun vote n'est accepte. Les autres `VACUUM` sont dans les
migrations, jouees au demarrage. Le sortir du verrou serait pire : une lecture
concurrente verrait un fichier a moitie reecrit.

Et la perte de voix par redemarrage etait accompagnee d'une recommandation
fondee sur une premisse fausse : « le RH ne peut pas regenerer de liens sans
invalider la consultation ». Il le peut. Regenerer des liens pour un groupe DEJA
DECLARE reutilise la cle existante -- `cle_publique()` ne cree que si elle est
absente -- donc l'empreinte de l'ensemble ne bouge pas. C'est precisement le
recours prevu, et il fonctionne.

**Sept constats de plus sur le meme fichier, dont deux tiennent.**

`historique_consultations` n'avait aucune contrainte d'unicite. Le scenario
avance -- double clic, reprise HTTP -- etait deja ferme ailleurs : la seconde
cloture constate l'etat vide et n'enregistre rien. La contrainte ajoutee couvre
le cas etroit qui restait, deux appels concurrents au meme horodatage.

Les messages critiques partaient sur `stdout` par `print()`. Sous systemd,
journald les capture -- ils ne sont donc pas perdus -- mais ils arrivent sans
niveau, ce qui empeche de filtrer un « CRITIQUE : dechiffrement impossible »
d'une trace ordinaire.

**Cinq constats ne tenaient pas**, et le detail vaut d'etre garde.

La detection de migration des jetons (« un jeton en clair de 64 caracteres
hexadecimaux serait ignore ») n'est pas atteignable : `token_urlsafe(24)` produit
32 caracteres, jamais 64. La migration ne concerne d'ailleurs que des bases
anterieures au 12/08, dont il n'existe plus aucune.

Les trois autres -- migrations non atomiques, `VACUUM` repete, croissance du
cache memoire -- decrivent des mecaniques exactes dont la portee ne se realise
pas : les migrations sont idempotentes et jouees au demarrage, le second
`VACUUM` ne s'execute que sur une base qui a besoin des deux migrations, et le
cache est purge a chaque ecriture -- donc a chaque signature emise, ce qui est
precisement le scenario de croissance decrit.

**Un dernier constat, et c'est le seul des onze qui touchait une garantie.** La
retention du cache de signatures se mesurait sur `time.time()`, l'horloge murale.
Un ajustement NTP, un changement manuel, un decalage au demarrage faisaient
varier la duree reelle : vers l'avant, le cache est purge trop tot et un votant
perd son rattrapage ; **vers l'arriere, il est conserve PLUS d'une heure** -- le
couple (empreinte du jeton, empreinte du message aveugle) restait en memoire
au-dela de ce que ce module annonce, sans que rien ne le signale.

Bascule sur `time.monotonic()`, qui ne recule jamais. Elle ne survit pas a un
redemarrage, mais ce cache non plus : il est en memoire, il meurt avec le
processus. Les deux autres usages de l'horloge -- la fenetre de douze mois
glissants d'`historique_consultations` -- gardent l'horloge murale, qui doit
traverser les redemarrages.

### Les 106 lignes de Rust, enfin lues

Dix audits ont liste `vera_blind_sig/src/lib.rs` dans leurs angles morts : deux
auditeurs ont tente de compiler et abandonne faute de chaine Rust, les autres ne
l'ont pas ouvert. C'etait le dernier trou reel du projet -- toute la non-liaison
repose sur ce fichier, et personne ne l'avait verifie.

Lu le 03/09/2026. **Trois points etablis, aucun correctif necessaire.**

**Aucune primitive n'est reimplementee.** Les cinq fonctions deserialisent une
cle DER, appellent une methode du crate `blind-rsa-signatures`, et convertissent
le resultat en octets. Aucune arithmetique, aucun calcul modulaire, aucun
hachage manuel. L'affirmation centrale du README tient.

**Le facteur d'aveuglement ne remonte jamais vers le serveur, et c'est
structurel.** `signer_aveugle` ne prend que la cle privee et le message
aveugle -- il ne recoit ni le secret, ni le message en clair, ni le randomizer.
Les deux fonctions qui manipulent le secret, `aveugler_message` et
`finaliser_signature`, ne sont appelees que dans le navigateur. La separation
tient a la signature des fonctions, pas a une convention d'appel.

**L'alea vient du crate** (`DefaultRng`), sans graine fournie ni generateur
maison.

**Une fragilite de forme, sans consequence aujourd'hui.** `unwrap_or_default()`
rendrait un randomizer vide si le crate n'en produisait pas ; la finalisation le
refuserait alors -- mais APRES que le serveur a signe et consomme le jeton, donc
le votant perdrait sa voix. Le parametre de type `Randomized` garantit sa
presence : le cas ne peut pas survenir tant qu'il ne change pas. Commente sur
place.


