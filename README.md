# Protocole VERA / ANCRE

*Agrégation à confidentialité différentielle, non-persistante.*

VERA publie un résultat collectif (sondage sensible, consultation interne)
sans jamais rendre lisible la contribution d'un individu — et le prouve.

- *Présentation et positionnement* : [README_VERA.md](README_VERA.md)
- *Modèle de menace (les 7 portes)* : [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)
- *Preuve reproductible (garantie eps-DP exacte = 0,5 via OpenDP)* : [validation_opendp.py](validation_opendp.py)
- *Porte 7 (tokens anonymes a usage unique, prototype)* : [vera_token.py](vera_token.py) — tests : [test_porte7.py](test_porte7.py)

## Antériorité (DOI Zenodo)

- v1.0 (2026-06-12) : https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) : https://doi.org/10.5281/zenodo.20671969

## État des 7 portes

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | Fermée (preuve OpenDP) |
| 2. MIA | Préliminaire (borne analytique) |
| 3. Canal temporel | Préliminaire |
| 4. Composition | Préliminaire (budget spécifié) |
| 5. Observateur réseau | Hors-périmètre, assumé |
| 6. Coercition | Hors-périmètre, assumé |
| 7. Différenciation « 49/1 » | Fermée (prototype, RFC 9474 à venir) |

## Limites assumées

L1 observateur réseau · L2 coercition · L3 petits effectifs (refus de publier
sous seuil) · L4 qualification RGPD anonymisation/pseudonymisation (avis
CNIL/DPO externe requis, non tranché).

## Historique

L'origine du projet (analyse audio Radio France, ère « VERA Radio ») est
conservée dans archive/ et dans les modules Rust vera-radio, vera-sdk,
vera-cli, vera-sib. Le cœur actuel du projet est le protocole
d'agrégation DP non-persistant décrit ci-dessus.

## Licence

Voir [LICENSE](LICENSE). Documents : CC-BY 4.0.
