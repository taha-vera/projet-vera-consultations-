# VERA Consultation

*Agrégation à confidentialité différentielle, non-persistante.*

VERA publie un résultat collectif (sondage sensible, consultation interne)
sans jamais rendre lisible la contribution d'un individu — et le prouve.

- *Modèle de menace complet (16 portes)* : [VERA_THREAT_MODEL_COMPLETE.md](VERA_THREAT_MODEL_COMPLETE.md)
- *Mécanisme de bruit en production* : [vera_dp_noise.py](vera_dp_noise.py) (OpenDP, Δ=2, scale=4, ε=0.5, bounds=(0,10000))
- *Persistance chiffrée de l'état (Portes 11, 14)* : [vera_persistance.py](vera_persistance.py) (SQLite WAL, Fernet/AES-128)
- *Porte 7 (signature aveugle RSABSSA, production)* : [vera_signature_manager.py](vera_signature_manager.py) — tests : [test_porte7.py](test_porte7.py)

## Antériorité (DOI Zenodo)

- v1.0 (2026-06-12) : https://doi.org/10.5281/zenodo.20668681
- v1.1 (2026-06-12, porte 7 fermée en prototype) : https://doi.org/10.5281/zenodo.20671969

## État des 16 portes (mis à jour 09/07/2026)

| Porte | État |
|---|---|
| 1. Mécanisme de bruit | Fermée — Δ=2, scale=4, ε=0.5 vérifié |
| 2. MIA générale | Fermée — AUC=0.6279, TPR@1%FPR=1.65% |
| 3. Canal temporel | Fermée — fuite sub-microseconde (0.209µs), inexploitable via réseau |
| 4. Composition séquentielle | Fermée — budget par population, vérifié empiriquement |
| 5. Observateur réseau | Hors-périmètre, assumé (VPN/Tor au choix utilisateur) |
| 6. Coercition | Hors-périmètre, limite partagée par tout système de vote |
| 7. Différenciation « 49/1 » | Fermée — signature aveugle RSABSSA RFC 9474, testée dans les deux sens |
| 8. Inférence outlier | Fermée — AUC=0.6279, TPR@1%FPR=1.65% |
| 9. Collusion émetteur/agrégateur | Fermée — secret admin distinct, comptes séparés |
| 10. Sondage binaire K_MIN | Fermée — effectif/fiable retirés de l'API |
| 11. Accès direct SQLite / clé RSA | Fermée — chiffrement Fernet/AES-128, salt PBKDF2 aléatoire, crash-testée |
| 12. Secret admin visible /proc | Limite assumée (contexte solo-root) |
| 13. Soustraction d'agrégats | Limite irréductible DP, atténuée par budget ε |
| 14. Non-persistance de l'état | Fermée — SQLite WAL, crash-testée (kill -9 réel) |
| 15. Trafic en clair (HTTP) | Fermée — HTTPS via Nginx + Let's Encrypt, redirection automatique verifiee |
| 16. Retention des logs applicatifs | Fermée — purge manuelle a cloture + logrotate 3 jours en filet de securite |

## Limites assumées

L1 observateur réseau · L2 coercition · L3 petits effectifs (refus de publier
sous seuil) · L4 qualification RGPD anonymisation/pseudonymisation (avis
CNIL/DPO externe requis, non tranché).


## Licence

Voir [LICENSE](LICENSE). Documents : CC-BY 4.0.
