#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le module Rust de VERA donne les RESULTATS OFFICIELS de la RFC 9474.

POURQUOI. Aucun test du depot ne confrontait le module a un resultat connu
d'avance : les tests existants verifient que signer puis verifier est coherent,
ce qu'une implementation fausse mais symetrique passerait aussi. La RFC 9474
publie en annexe A des vecteurs de test (cle, message, facteur d'aveuglement,
message aveugle, signature aveugle, signature finale). Ils sont deterministes
des qu'on fixe les aleas : on peut donc les rejouer.

LE VECTEUR. A.1, RSABSSA-SHA384-PSS-Randomized : c'est la variante que fixe
src/lib.rs (Sha384, PSS, Randomized). Les valeurs viennent du fichier de tests
du crate blind-rsa-signatures 0.17.2, recoupees avec le texte de la RFC
(debut de p, q, n, msg, prefixe, sel, inv, message aveugle, signature aveugle et
signature finale). tests/donnees/rfc9474_a1_sha384_pss_randomized.json.

CE QUE LE TEST VERIFIE (module `vera_blind_sig`, tel que l'API l'appelle)
  1. signer_aveugle(cle privee du vecteur, message aveugle) rend EXACTEMENT la
     signature aveugle de la RFC ;
  2. finaliser_signature(..., secret = inv, prefixe) rend EXACTEMENT la signature
     de la RFC ;
  3. verifier_signature accepte cette signature ;
  4. verifier_signature la refuse si on change un octet du message, de la
     signature ou du prefixe, et si le prefixe est d'une autre longueur
     (erreur ou refus, jamais « valide »).

ATTENTION : la cle des vecteurs de la RFC fait 4096 bits ; celle de VERA en production
fait 2048 bits. Le code est le meme, la taille differe : ce test n'exerce pas le
chemin 2048 bits (couvert, lui, par l'aller-retour de test_signature_production.py).

CE QU'IL NE VERIFIE PAS. L'aveuglement lui-meme (aveugler_message) tire ses
propres aleas : on ne peut pas lui imposer ceux du vecteur depuis Python. Il
est couvert par test_signature_production.py (aller-retour). Un vecteur ne prouve
pas non plus la non-liaison : voir LIMITS.md.
"""

import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
FICHIER = RACINE / "tests" / "donnees" / "rfc9474_a1_sha384_pss_randomized.json"

try:
    import vera_blind_sig as vbs
except ImportError as e:  # pragma: no cover
    print(f"IGNORE : {e}")
    raise SystemExit(2)
if not callable(getattr(vbs, "finaliser_signature", None)):
    print("IGNORE : le module Rust n'est pas compile.")
    raise SystemExit(2)

echecs = []


def verifier(condition, message, detail=""):
    if condition:
        print(f"  OK  {message}")
    else:
        echecs.append(message + ("\n      " + detail if detail else ""))
        print(f"  ECHEC  {message}")


def entier(h):
    return int(h, 16)


def der_long(n):
    b = n.to_bytes((n.bit_length() + 7) // 8 or 1, "big")
    return bytes([0x80 | len(b)]) + b


def der(tag, contenu):
    n = len(contenu)
    return bytes([tag]) + (bytes([n]) if n < 128 else der_long(n)) + contenu


def der_int(x):
    b = x.to_bytes((x.bit_length() + 7) // 8 or 1, "big")
    if b[0] & 0x80:
        b = b"\x00" + b
    return der(0x02, b)


OID_RSA = bytes.fromhex("06092a864886f70d0101010500")   # rsaEncryption + NULL
v = json.loads(FICHIER.read_text())["vecteur"]
p, q, n, e, d = (entier(v[k]) for k in ("p", "q", "n", "e", "d"))
verifier(p * q == n, "0a. (coherence du vecteur) p * q = n")
verifier(pow(pow(0x1234567, e, n), d, n) == 0x1234567, "0b. (coherence du vecteur) d est bien l'inverse de e")

rsa_pub = der(0x30, der_int(n) + der_int(e))
spki = der(0x30, der(0x30, OID_RSA) + der(0x03, b"\x00" + rsa_pub))
rsa_priv = der(0x30, b"".join(der_int(x) for x in (
    0, n, e, d, p, q, d % (p - 1), d % (q - 1), pow(q, -1, p))))
pkcs8 = der(0x30, der_int(0) + der(0x30, OID_RSA) + der(0x04, rsa_priv))

msg = bytes.fromhex(v["msg"])
prefixe = bytes.fromhex(v["msg_prefix"])
inv = bytes.fromhex(v["inv"][2:] if v["inv"].startswith("0x") else v["inv"])
blinded = bytes.fromhex(v["blinded_msg"])
blind_sig = bytes.fromhex(v["blind_sig"])
sig = bytes.fromhex(v["sig"])
verifier(len(prefixe) == 32 and len(blinded) == 512 and len(sig) == 512 and len(inv) == 512,
         "0c. longueurs du vecteur : prefixe 32, message aveugle 512, signature 512, inv 512 (cle de 4096 bits)",
         f"{len(prefixe)} {len(blinded)} {len(sig)} {len(inv)}")

# --- 1. signature aveugle ----------------------------------------------------
sortie = bytes(vbs.signer_aveugle(pkcs8, blinded))
verifier(sortie == blind_sig, "1. signer_aveugle rend EXACTEMENT la signature aveugle de la RFC",
         f"obtenu {sortie[:12].hex()}..., attendu {blind_sig[:12].hex()}...")

# --- 2. finalisation ----------------------------------------------------------
try:
    final = bytes(vbs.finaliser_signature(spki, msg, blinded, inv, blind_sig, prefixe))
except Exception as ex:  # noqa: BLE001
    final = b""
    print("   finaliser_signature a leve :", ex)
verifier(final == sig, "2. finaliser_signature rend EXACTEMENT la signature finale de la RFC",
         f"obtenu {final[:12].hex()}..., attendu {sig[:12].hex()}...")

# --- 3 et 4. verification ------------------------------------------------------
def accepte(m, s, pre):
    try:
        return bool(vbs.verifier_signature(spki, m, s, pre))
    except Exception:  # noqa: BLE001
        return False


verifier(accepte(msg, sig, prefixe), "3. verifier_signature accepte la signature de la RFC")


def mute(b, i=0):
    return bytes([b[i] ^ 1]) + b[1:] if i == 0 else b[:i] + bytes([b[i] ^ 1]) + b[i + 1:]


verifier(not accepte(mute(msg), sig, prefixe), "4a. un octet du message change : refuse")
verifier(not accepte(msg, mute(sig), prefixe), "4b. un octet de la signature change : refuse")
verifier(not accepte(msg, sig, mute(prefixe)), "4c. un octet du prefixe change : refuse")
verifier(not accepte(msg, sig, mute(prefixe, 31)), "4d. dernier octet du prefixe change : refuse")
verifier(not accepte(msg, mute(sig, 255), prefixe), "4e. dernier octet de la signature change : refuse")
verifier(not accepte(msg + b"\x00", sig, prefixe), "4f. un octet ajoute au message : refuse")
try:
    r = bool(vbs.verifier_signature(spki, msg, sig, prefixe[:31]))
except Exception:  # noqa: BLE001
    r = False
verifier(not r, "4g. prefixe de 31 octets : refuse (erreur ou faux)")

print()
if echecs:
    print(f"ECHEC : {len(echecs)} verification(s).\n")
    for x in echecs:
        print("  - " + x)
    sys.exit(1)
print("OK : le module Rust reproduit les resultats de la RFC 9474, annexe A.1.")
sys.exit(0)
