import { readFileSync, writeFileSync } from 'fs';
import { RSABSSA } from '@cloudflare/blindrsa-ts';

const suite = RSABSSA.SHA384.PSS.Randomized();

// 1. Charger la cle publique Rust (SPKI DER) et l'importer
const pkDer = readFileSync('/root/crypto_test/pk_rust.der');
const publicKey = await crypto.subtle.importKey(
    'spki', pkDer, { name: 'RSA-PSS', hash: 'SHA-384' }, true, ['verify']
);

// 2. Le message a signer (ce que serait un token de vote)
const messageTexte = 'vote-token-test-2026';
const msg = new TextEncoder().encode(messageTexte);

// 3. Preparer + aveugler (cote CLIENT en vrai)
const prepared = suite.prepare(msg);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);

// 4. Sauvegarder ce dont Rust a besoin pour signer, et ce dont on aura besoin pour finaliser
writeFileSync('/root/crypto_test/blinded_msg.bin', Buffer.from(blindedMsg));
writeFileSync('/root/crypto_test/prepared.bin', Buffer.from(prepared));
writeFileSync('/root/crypto_test/inv.bin', Buffer.from(inv));
writeFileSync('/root/crypto_test/message.txt', messageTexte);

console.log('ETAPE 1 (JS) OK - message aveugle cote client');
console.log('  message prepare:', prepared.length, 'octets');
console.log('  message aveugle:', blindedMsg.length, 'octets');
console.log('  inv (secret):', inv.length, 'octets');
