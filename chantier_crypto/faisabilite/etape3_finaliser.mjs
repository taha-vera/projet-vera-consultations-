import { readFileSync } from 'fs';
import { RSABSSA } from '@cloudflare/blindrsa-ts';

const suite = RSABSSA.SHA384.PSS.Randomized();

// Charger la cle publique et tout ce qu'on a sauvegarde
const pkDer = readFileSync('/root/crypto_test/pk_rust.der');
const publicKey = await crypto.subtle.importKey(
    'spki', pkDer, { name: 'RSA-PSS', hash: 'SHA-384' }, true, ['verify']
);

const prepared = new Uint8Array(readFileSync('/root/crypto_test/prepared.bin'));
const inv = new Uint8Array(readFileSync('/root/crypto_test/inv.bin'));
const blindSig = new Uint8Array(readFileSync('/root/crypto_test/blind_sig.bin'));
const messageTexte = readFileSync('/root/crypto_test/message.txt', 'utf8');

console.log('Signature aveugle recue de Rust:', blindSig.length, 'octets');

// ETAPE 3 : finaliser (definaliser) cote CLIENT
const signature = await suite.finalize(publicKey, prepared, inv, blindSig);
console.log('ETAPE 3 (JS) OK - signature finalisee:', signature.length, 'octets');

// ETAPE 4 : VERIFIER le token final
const msg = new TextEncoder().encode(messageTexte);
const valide = await suite.verify(publicKey, signature, prepared);

console.log('');
console.log('=== RESULTAT DU TEST DE BOUT EN BOUT ===');
if (valide) {
    console.log('SUCCES TOTAL : signature VALIDE');
    console.log('  -> aveugle(JS) -> signe(Rust) -> finalise(JS) -> verifie: OK');
    console.log('  -> Le refactor crypto cote client est FAISABLE.');
} else {
    console.log('ECHEC : la signature finale n est pas valide.');
    console.log('  -> il y a un desalignement a diagnostiquer.');
}
