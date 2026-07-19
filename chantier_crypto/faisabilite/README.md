# Faisabilite du pont crypto Rust <-> JS -- PROUVEE le 19/07/2026

Test de bout en bout reussi : le flux aveugle(JS) -> signe(Rust) -> finalise(JS)
-> verifie produit une signature VALIDE.

Conclusions etablies :
- La cle publique Rust (blind-rsa-signatures, to_der) est au format SPKI,
  directement importable par WebCrypto (crypto.subtle.importKey 'spki',
  RSA-PSS, SHA-384, 2048 bits). Aucune conversion PKCS1->SPKI necessaire.
- blindrsa-ts (RSABSSA.SHA384.PSS.Randomized) aveugle un message que
  vera_blind_sig.signer_aveugle (Rust) accepte et signe.
- La signature finalisee cote JS est valide.
- Tailles : message aveugle 256o, signature aveugle 256o, inv 256o, prepared 52o.

=> Le serveur peut ne faire QUE signer_aveugle. L'aveuglement et la
   finalisation peuvent vivre dans le navigateur du votant. L'unlinkability
   devient realisable.

Etapes du test (dans ce dossier) :
- test_import_cle.mjs : importe la cle Rust dans WebCrypto
- etape1_aveugler.mjs : JS aveugle un message avec la cle Rust
- (etape 2 : Python/Rust signe le message aveugle -- voir vera_blind_sig)
- etape3_finaliser.mjs : JS finalise + verifie -> VALIDE

PROCHAINE ETAPE : le POINT DUR = autorisation du votant. Comment le serveur
autorise un vote unique SANS pouvoir lier l'autorisation au token final.
