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
