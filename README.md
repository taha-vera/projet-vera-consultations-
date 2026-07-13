# VERA Consultation

*Agrégation à confidentialité différentielle, non-persistante.*

VERA publie un résultat collectif (sondage sensible, consultation interne)
sans jamais rendre lisible la contribution d'un individu — et le prouve.

- *Modèle de menace complet (17 portes)* : [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)
- *Mécanisme de bruit en production* : [vera_dp_noise.py](vera_dp_noise.py) (OpenDP, Δ=2, scale=4, ε=0.5, bounds=(0,10000))
- *Persistance chiffrée de l'état (Portes 11, 14)* : [vera_persistance.py](vera_persistance.py) (SQLite WAL, Fernet/AES-128)
- *Porte 7 (signature aveugle RSABSSA, production)* : [vera_signature_manager.py](vera_signature_manager.py) — tests : [test_porte7.py](test_porte7.py)

## Antériorité (DOI Zenodo)

- v1.0 (2026-06-12) : https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) : https://doi.org/10.5281/zenodo.20671969

## État des 17 portes (mis à jour 13/07/2026)

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | Fermée — Δ=2, scale=4, ε=0.5 vérifié |
| 2. MIA générale | Fermée — AUC=0.6209, IC95% [0.6185, 0.6232], borne théorique 0.6225 incluse (N=100 000, bootstrap) |
| 3. Canal temporel | Fermée — fuite sub-microseconde (0.209µs), inexploitable via réseau |
| 4. Composition séquentielle | Fermée — budget par population, vérifié empiriquement |
| 5. Observateur réseau | Hors-périmètre, assumé (VPN/Tor au choix utilisateur) |
| 6. Coercition | Hors-périmètre, limite partagée par tout système de vote |
| 7. Différenciation « 49/1 » | Fermée — signature aveugle RSABSSA RFC 9474, testée dans les deux sens |
| 8. Inférence outlier | Fermée — AUC=0.6209, IC95% [0.6185, 0.6232] (même mesure que Porte 2) |
| 9. Collusion émetteur/agrégateur | Fermée — secret admin distinct, comptes séparés |
| 10. Sondage binaire K_MIN | Fermée — effectif/fiable retirés de l'API |
| 11. Accès direct SQLite / clé RSA | Fermée — chiffrement Fernet/AES-128, salt PBKDF2 aléatoire, crash-testée |
| 12. Secret admin visible /proc | Limite assumée (contexte solo-root) |
| 13. Soustraction d'agrégats | Limite irréductible DP, atténuée par budget ε |
| 14. Non-persistance de l'état | Fermée — SQLite WAL, crash-testée (kill -9 réel) |
| 15. Trafic en clair (HTTP) | Fermée — HTTPS via Nginx + Let's Encrypt, redirection automatique verifiee |
| 16. Retention des logs applicatifs | Fermée — purge manuelle a cloture + logrotate 3 jours en filet de securite |
| 17. Correlation temporelle (horodatage_unix) | Limite assumee — protection reelle via K_MIN=100, pas via masquage du timing |

## Corrections suite à audit de code (13/07/2026)

Un audit du code réel (pas seulement de la documentation) a révélé et permis de corriger cinq points, tous vérifiés empiriquement :

- **Bug critique corrigé** : le résultat bruité est désormais figé après la première publication (table resultats_publies). Auparavant, chaque appel à /api/rh/resultats re-tirait du bruit, ce qui aurait permis de moyenner plusieurs tirages et de contourner la garantie ε. Vérifié : 5 appels successifs renvoient un résultat identique.
- **Garde worker unique** : le service refuse de démarrer avec plusieurs workers (l'état DP en mémoire n'est pas partagé entre processus). Protège la composition ε (Porte 4) par construction.
- Endpoints de test retirés de la production (ne consomment plus de tokens réels).
- Anti-bruteforce corrigé pour lire l'IP réelle derrière le reverse proxy.
- Schéma SQLite complété pour un déploiement propre from scratch.

Détail complet et preuves dans VERA_THREAT_MODEL_COMPLETE.md et VERA_CHALLENGE_REGISTER.md.

## Limites assumées

L1 observateur réseau · L2 coercition · L3 petits effectifs (refus de publier
sous seuil) · L4 qualification RGPD anonymisation/pseudonymisation (avis
CNIL/DPO externe requis, non tranché).


## Licence

Voir [LICENSE](LICENSE). Documents : CC-BY 4.0.
