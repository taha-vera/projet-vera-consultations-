import { readFileSync } from 'fs';

// Charger la cle publique DER (SPKI) generee par la lib Rust
const pkDer = readFileSync('/root/crypto_test/pk_rust.der');
console.log('Cle publique DER chargee:', pkDer.length, 'octets');

// Tenter de l'importer via WebCrypto (ce que blindrsa-ts utilise)
try {
    const publicKey = await crypto.subtle.importKey(
        'spki',
        pkDer,
        { name: 'RSA-PSS', hash: 'SHA-384' },
        true,
        ['verify']
    );
    console.log('SUCCES: cle Rust importee par WebCrypto');
    console.log('  Algorithme:', publicKey.algorithm.name);
    console.log('  Hash:', publicKey.algorithm.hash.name);
    console.log('  Taille modulus:', publicKey.algorithm.modulusLength, 'bits');
} catch (e) {
    console.log('ECHEC import:', e.message);
}
