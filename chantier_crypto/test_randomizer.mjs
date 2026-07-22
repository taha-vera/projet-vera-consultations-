import { RSABSSA } from '@cloudflare/blindrsa-ts';
const suite = RSABSSA.SHA384.PSS.Randomized();
const K = crypto.getRandomValues(new Uint8Array(32));
const prepared = suite.prepare(K);
console.log('K:', K.length, 'octets');
console.log('prepared:', prepared.length, 'octets');
console.log('prepared commence par 32 octets de randomizer puis K ?');
// Verifier si prepared = randomizer(32) || K
const suffixe = prepared.slice(prepared.length - K.length);
const memeQueK = Buffer.compare(Buffer.from(suffixe), Buffer.from(K)) === 0;
console.log('  les', K.length, 'derniers octets de prepared == K :', memeQueK);
console.log('  donc randomizer =', prepared.length - K.length, 'octets prefixes');
