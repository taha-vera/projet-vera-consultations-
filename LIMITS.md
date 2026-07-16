# VERA — Limites assumees

Ce document enonce ce que VERA NE protege PAS, ou protege seulement sous
certaines conditions. Un modele de menace qui cache ses limites n'a aucune
valeur.

## 1. Le contenu des reponses est protege ; la participation ne l'est pas toujours

VERA garantit qu'on ne peut pas apprendre COMMENT un individu a repondu (bruit
differentiel, eps=0.5). Il ne garantit PAS, en toute generalite, qu'on ne puisse
pas apprendre QU'UN individu a participe.

L'effectif total N d'un departement est publie exact. Cela repose sur un modele
d'adjacence par SUBSTITUTION : sous ce modele N est invariant, le publier ne
coute rien. Mais sous un modele d'AJOUT/RETRAIT, publier N exact revele la
participation. Si le simple fait d'avoir repondu est sensible dans votre
contexte, VERA sous sa forme actuelle ne protege pas cette information.

Mitigation partielle : l'effectif exact des cohortes sous le seuil K_MIN n'est
pas expose (message de refus et tableau de bord). Au-dessus du seuil, N est
publie exact.

## 2. Precision limitee sur les petites cohortes

A eps=0.5, l'erreur sur chaque option est d'environ 12% de l'effectif au 95e
centile pour n=100, et descend sous 5% seulement a partir de n=240. VERA refuse
de publier sous 240 participants. C'est le prix de l'anonymat a ce niveau de
garantie. VERA n'est adapte qu'aux organisations dont les groupes consultes
depassent 240 personnes.

## 3. VERA donne une tendance, pas un decompte exact

Le resultat publie est une estimation bruitee. Il distingue une majorite claire
d'une minorite, mais ne tranche pas un vote serre a quelques points (52/48).

## 4. Observateur reseau et metadonnees

VERA ne protege pas contre un observateur du reseau (qui vote, quand). La
protection contre la correlation temporelle passe par K_MIN, pas par un masquage
du timing. L'utilisateur soucieux de cet aspect doit utiliser un canal
anonymisant (VPN/Tor).

## 5. Coercition

Comme tout systeme de vote, VERA ne protege pas contre la coercition physique
directe. Limite partagee par l'ensemble des systemes de ce type.

## 6. Confiance dans l'organisateur au moment de l'emission

L'organisateur (RH) connait, au moment d'emettre les jetons, la correspondance
identite/departement. VERA empeche que cette information se propage dans le
traitement des reponses, mais ne l'efface pas cote organisateur. La cryptographie
ne peut pas retirer cette connaissance initiale.

## 7. Perimetre : consultation d'opinion, pas donnees de sante

VERA agrege des OPINIONS. Il n'est PAS concu pour des donnees de sante de
patients au sens RGPD article 9 (HDS, AIPD, MR-004 non couverts). Il peut servir
a des consultations de climat social en etablissement de sante, pas a traiter
des donnees cliniques individuelles.

## 8. Canal temporel du tableau de bord RH

Le tableau de bord (`/api/rh/etat_departements`) est un compteur live. Un
organisateur qui le consulte de façon répétée peut observer, au-dessus du
seuil K_MIN, l'arrivée des votes en temps réel (chaque vote incrémente le
compteur). Cela révèle le *rythme* de participation et l'instant de chaque
vote, mais jamais le *contenu* d'une réponse.

C'est la même classe de canal que la Porte 3 (corrélation temporelle) : la
participation et son timing ne sont pas masqués, seule la réponse l'est. Sous
le seuil K_MIN, l'effectif exact n'est de toute façon pas exposé (voir §1).
Pour un contexte où le timing de participation serait lui-même sensible, il
faudrait un rafraîchissement différé ou un arrondi du compteur — non
implémenté à ce jour, documenté ici comme limite assumée.
