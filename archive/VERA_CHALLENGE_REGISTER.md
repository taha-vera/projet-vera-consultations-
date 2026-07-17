# VERA -- Registre des challenges IA

## Objectif
Atteindre la limite 2026 : un tour complet des IA accessibles ne produit
aucune nouvelle porte non deja traitee ou documentee comme limite assumee.

## Critere d'arret pratique
Quand N sessions fraiches consecutives (toutes IA du tableau, prompt
standard, document VERA_AUDIT_REFERENCE.md soumis tel quel) ne produisent
aucune nouvelle porte --> condition d'arret atteinte --> passage au
deploiement.

## Prompt standard utilise
Voir VERA_AUDIT_REFERENCE.md + prompt adversarial type :
"Tu es un auditeur de securite senior specialise en DP et sondages anonymes.
Ton mandat : trouver des failles, pas valider ce qui existe. [COLLER
VERA_AUDIT_REFERENCE.md]. Questions : A) Portes fragiles meme si Fermee ?
B) Vecteurs non couverts par les 17 portes ? C) Limites assumees
defensibles ou negligence deguisee ? D) Note /10 et point le plus urgent.
Commence par le probleme le plus grave."

---

## Registre des sessions

| Date | IA | Session | Nouvelles portes trouvees | Statut | Note |
|---|---|---|---|---|---|
| 30/06/2026 | Multi-IA (4 systemes) | 1 | Porte 10 (sondage binaire K_MIN) | Traitee | Premiere identification canal binaire |
| 02/07/2026 | Multi-IA | 1 | Porte 13 (soustraction agregats) | Assumee | Limite irreductible DP |
| 04/07/2026 | GPT, Gemini, Fable 5 | 1 | effectif/fiable = canal binaire | Traitee | Champs retires de l API |
| 04/07/2026 | Fable 5 | 1 | Salt PBKDF2 fixe | Traitee | Salt aleatoire deploye |
| 04/07/2026 | Fable 5 | 1 | bounds=(0,100) vs K_MIN=100 contradiction | Traitee | Bounds elargis a (0,10000) |
| 04/07/2026 | Fable 5 | 1 | Delta=10 sur-calibre | Traitee | Recalibration Delta=2 scale=4 |
| 05/07/2026 | Revue interne | 1 | Porte 11 (SQLite cle RSA en clair) | Traitee | Fernet/AES-128 + salt aleatoire |
| 05/07/2026 | Revue interne | 1 | Porte 12 (secret admin /proc) | Assumee | Solo-root, defensible |
| 05/07/2026 | Revue interne | 1 | Porte 14 (non-persistance etat) | Traitee | SQLite WAL, crash-teste + reboot |
| 09/07/2026 | Fable 5 | 1 | Porte 15 (HTTP en clair) | Traitee | HTTPS Nginx + Let Encrypt |
| 09/07/2026 | Revue interne | 1 | Porte 16 (retention logs) | Traitee | Purge manuelle + logrotate |
| 09/07/2026 | Fable 5 | 1 | Porte 17 (horodatage_unix) | Assumee | Protection via K_MIN, pas masquage |
| 09/07/2026 | Fable 5 | 1 | Protocole statistique invalide | N/A | Methodologie, pas une porte |

---

## Synthese par IA

| IA | Sessions | Nouvelles portes | Derniere session vierge |
|---|---|---|---|
| Claude (cette session) | Multiple | 14, 15, 16, 17 (co-identifiees) | -- |
| Fable 5 | 3 | 10, salt PBKDF2, bounds, Delta, 17 | Non |
| GPT / Gemini | 2 | effectif/fiable, 11, 12 | Non |
| [prochaine IA] | 0 | -- | -- |

---

## Prochaines sessions planifiees

Tour 1 -- a realiser en sessions fraiches :
- Claude (nouvelle conversation, sans contexte de cette session)
- GPT-4o (ChatGPT) -- 09/07/2026 : 0 nouvelle porte. Bruteforce resoudre_code deja couvert (5 echecs/IP, blocage 5min). Nuances valides : timing Fernet Porte 3, race condition Porte 4 (meme point que Copilot).
- Gemini 1.5 Pro -- 12/07/2026 : 0 nouvelle porte. Nuances : Porte 3 attaquant local, Porte 11 substitution cle sans contexte (limite assumee), backup absent (deja documente).
- Mistral Large -- 12/07/2026 : 1 point traite. AUC=0.6279 > borne theorique soulevee -- re-mesure N=100000 confirme AUC=0.6209 dans IC95% [0.6185,0.6232], borne 0.6225 incluse. Porte 2 confirmee fermee.
- Fable 5 -- 13/07/2026 : SEULE IA a lire le CODE reel (via URLs GitHub) au lieu de la description. A trouve 4 VRAIS BUGS que les 4 autres IA avaient manques :
  1. CRITIQUE : bruit DP re-tire a chaque appel /api/rh/resultats -> moyennage possible -> garantie epsilon cassee des la 2e lecture. Corrige (resultat fige, table resultats_publies). Verifie 5 appels identiques.
  2. Endpoints /api/test/* en prod brulaient de vrais tokens (DoS). Corrige (404).
  3. Schema salt_hex manquant -> deploiement from scratch cassait. Corrige.
  4. Anti-bruteforce voyait 127.0.0.1 derriere Nginx. Corrige (X-Real-IP, teste 5x404+429).

Document a soumettre : VERA_AUDIT_REFERENCE.md (version 1.0, 09/07/2026)
Prompt : prompt adversarial standard (voir ci-dessus)

Si aucune nouvelle porte n'emerge sur ce tour --> limite 2026 atteinte.

---

## Historique des versions du document de reference

| Version | Date | Changements majeurs |
|---|---|---|
| 1.0 | 09/07/2026 | Creation, 17 portes, parametres DP recalibres, HTTPS |

- Meta AI (Llama) -- 13/07/2026 : audit post-correction. Point souleve : race condition lors du figeage du resultat (concurrence entre verification deja_publie et persistance). FAUX POSITIF -- le with verrou (threading.Lock global) englobe toute la section critique, double consommation impossible. Verifie dans le code. Autres points : reprises de limites deja assumees (P13, P17).