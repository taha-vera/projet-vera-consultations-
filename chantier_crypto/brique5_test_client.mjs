// brique5_test_client.mjs
// Test du flux client complet contre le VRAI serveur HTTP.
//   0. GET  /api/cle_publique        -> importKey
//   1. [JS] prepare + blind
//   2. login RH -> generer_autorisations -> POST /api/signer_aveugle
//   3. [JS] finalize
//   4. [JS] verify(pk, signature, prepared)  DOIT etre true
import { RSABSSA } from '@cloudflare/blindrsa-ts';

const BASE = 'https://vera-consultation.duckdns.org';
const suite = RSABSSA.SHA384.PSS.Randomized();
const toHex = (u8) => Buffer.from(u8).toString('hex');
const fromHex = (h) => new Uint8Array(Buffer.from(h, 'hex'));

// --- 0. Cle publique du serveur ---
const rPk = await fetch(`${BASE}/api/cle_publique`);
const { cle_publique_hex, empreinte_sha256 } = await rPk.json();
const pkDer = fromHex(cle_publique_hex);
const publicKey = await crypto.subtle.importKey(
    'spki', pkDer, { name: 'RSA-PSS', hash: 'SHA-384' }, true, ['verify']
);
console.log('0. Cle publique importee. Empreinte:', empreinte_sha256.slice(0,16), '...');

// --- 1. Preparer + aveugler (CLIENT) ---
const messageTexte = 'vote-token-brique5-' + Date.now();
const msg = new TextEncoder().encode(messageTexte);
const prepared = suite.prepare(msg);
const { blindedMsg, inv } = await suite.blind(publicKey, prepared);
console.log('1. Message aveugle:', blindedMsg.length, 'octets');

// --- 2a. Login RH ---
const rLogin = await fetch(`${BASE}/api/rh/connexion`, {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ identifiant: 'asso_acer', mot_de_passe: '***REMOVED***' })
});
const cookie = rLogin.headers.get('set-cookie');
console.log('2a. Login RH:', (await rLogin.json()).statut);

// --- 2b. Generer un jeton d'autorisation ---
const rGen = await fetch(`${BASE}/api/rh/generer_autorisations`, {
    method: 'POST', headers: {'Content-Type':'application/json', 'Cookie': cookie},
    body: JSON.stringify({ departement: 'Test-Brique5', quantite: 1 })
});
const jeton = (await rGen.json()).autorisations[0].jeton;
console.log('2b. Jeton obtenu:', jeton.slice(0,12), '...');

// --- 2c. Signer a l'aveugle (SERVEUR) ---
const rSig = await fetch(`${BASE}/api/signer_aveugle`, {
    method: 'POST', headers: {'Content-Type':'application/json', 'Cookie': cookie},
    body: JSON.stringify({ jeton_autorisation: jeton, message_aveugle_hex: toHex(blindedMsg) })
});
const sigJson = await rSig.json();
if (!sigJson.signature_aveugle_hex) { console.log('ECHEC signer_aveugle:', sigJson); process.exit(1); }
const blindSig = fromHex(sigJson.signature_aveugle_hex);
console.log('2c. Signature aveugle recue:', blindSig.length, 'octets');

// --- 3. Finaliser (CLIENT) ---
const signature = await suite.finalize(publicKey, prepared, inv, blindSig);
console.log('3. Signature finalisee:', signature.length, 'octets');

// --- 4. Verifier --- (sur prepared, PAS msg : variante Randomized)
const valide = await suite.verify(publicKey, signature, prepared);
console.log('');
console.log('=== RESULTAT BRIQUE 5 (client <-> vrai serveur HTTP) ===');
console.log(valide ? 'SUCCES : signature VALIDE de bout en bout' : 'ECHEC : desalignement');
process.exit(valide ? 0 : 1);
