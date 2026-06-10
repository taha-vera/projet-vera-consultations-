# VERA / ANCRE — Agrégation à confidentialité différentielle, non-persistante

*Auteur :* Taha Houari · tahahouari@hotmail.fr
*Dépôt :* github.com/taha-vera/Protocole-Vera
*Date :* 2026-06-10

## Qu'est-ce que VERA

VERA est une infrastructure qui publie un résultat collectif (sondage, consultation, agrégat de signaux) *sans jamais rendre lisible la contribution d'un individu, et en le prouvant.* Trois propriétés :

1. *Non-persistance structurelle* — la donnée brute traverse le pipeline sans y être stockée. Ce n'est pas une suppression a posteriori mais une propriété d'architecture : il n'y a pas d'emplacement de stockage.
2. *Bruit DP avant publication* — seul un agrégat bruité par confidentialité différentielle est publié. La protection vise le résultat lui-même (ex. « 1 réponse sur 100 » ne doit pas isoler une personne), pas seulement les données stockées.
3. *Preuve déplacée* — au lieu de prouver « j'ai effacé à temps » (un négatif, fragile), VERA prouve « le système est structurellement incapable de retenir ou de révéler l'individu » (propriété attestable).

## Ce que la preuve établit

Le fichier validation_opendp.py est reproductible (python validation_opendp.py, dépendance : opendp). Il établit :

- *Garantie ε-DP exacte = 0,5*, certifiée par OpenDP via meas.map() — calcul analytique, sans Monte Carlo, sans sampler maison.
- *MIA pire cas borné* : l'AUC de l'attaquant d'appartenance optimal est 0,6209, sous la borne théorique 0,6225 = e^ε/(1+e^ε).
- *Composition* : le coût de k requêtes séquentielles est tabulé ; au-delà de k=4 la protection s'effondre, d'où budget plafonné + partition par token.

Validation préliminaire indépendante (Python pur, Android/Termux) : sampler exact Canonne-Kamath-Steinke 2020 conforme (z=−0,19), canal temporel sans fuite détectable (écart 2,83 % dans le bruit de mesure).

## Ce que VERA n'est PAS / limites assumées

- *Pas un système de vote* : le décompte exact lui est interdit par le bruit. Terrain visé : sondage sensible et consultation, pas l'élection.
- *Pas une invention* : assemblage correct de primitives connues (DP, non-persistance), sans mécanisme nouveau.
- *L1* Observateur réseau — hors périmètre (IP vue en amont).
- *L2* Coercition — un répondant peut prouver volontairement sa réponse.
- *L3* Petits effectifs — sous un seuil N, anonymat indélivrable (refus de publier).
- *L4* Qualification RGPD (anonymisation vs pseudonymisation, art. 5(1)(e)) — relève d'un avis CNIL / DPO, non tranché par ce dépôt.

## Positionnement

VERA vise le paradoxe de la preuve d'effacement (RGPD art. 5(1)(e)) : certifier une non-persistance structurelle plutôt que prouver une suppression par enregistrement. Ce positionnement requiert une validation juridique externe (L4), identifiée comme étape ouverte.

## Licence

Open source — voir le dépôt.
