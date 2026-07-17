# =====================================================================
# VERA - Porte 7 : tokens anonymes a usage unique (un par individu/epoque)
# Ferme l'attaque par differenciation de cohortes (Dinur-Nissim 2003).
#
# AVERTISSEMENT (discipline post-DLap) : la primitive de signature aveugle
# est ici implementee a la main pour valider la LOGIQUE. Avant production,
# la remplacer par une implementation auditee (RSABSSA, RFC 9474 ;
# impl. de reference : Cloudflare blindrsa-ts).
# =====================================================================
import hashlib
import secrets
from cryptography.hazmat.primitives.asymmetric import rsa


# AVERTISSEMENT CRYPTO : ce FDH maison (SHA-256 etendu, sans PSS) est FORGEABLE
# par homomorphie RSA : sig(a)*sig(b) = sig(a*b) mod n. NE PAS utiliser en
# production. La partition par epoque (logique) est validee ; la PRIMITIVE doit
# etre remplacee par RSABSSA / RFC 9474.
def _fdh(data: bytes, n: int) -> int:
    """Full-Domain Hash : etend SHA-256 a la taille du module n."""
    nbytes = (n.bit_length() + 7) // 8
    out = b""
    c = 0
    while len(out) < nbytes:
        out += hashlib.sha256(data + c.to_bytes(4, "big")).digest()
        c += 1
    return int.from_bytes(out[:nbytes], "big") % n


class Emetteur:
    """Delivre au plus UN token par (individu, epoque), sans voir le token."""
    def __init__(self):
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pub = k.public_key().public_numbers()
        priv = k.private_numbers()
        self.n, self.e, self.d = pub.n, pub.e, priv.d
        self.emis = set()
        # MINIMISATION (porte 9) : l'emetteur ne conserve AUCUNE trace du message
        # aveugle. Rien cote emetteur ne permet de relier un individu a son token.

    def cle_publique(self):
        return self.n, self.e

    def signer_aveugle(self, individu_id: str, epoque: str, msg_aveugle: int) -> int:
        cle = (individu_id, epoque)
        if cle in self.emis:
            raise PermissionError("REFUS: token deja emis pour cet individu cette epoque")
        self.emis.add(cle)
        return pow(msg_aveugle, self.d, self.n)


class Client:
    """Genere un serial secret, l'aveugle, recupere la signature valide."""
    def __init__(self, n: int, e: int):
        self.n, self.e = n, e
        self.serial = secrets.token_bytes(32)
        self.r = None

    def aveugler(self, epoque: str) -> int:
        while True:
            r = secrets.randbelow(self.n - 2) + 2
            try:
                pow(r, -1, self.n)
                break
            except ValueError:
                continue
        self.r = r
        return (_fdh(self.serial + epoque.encode(), self.n) * pow(r, self.e, self.n)) % self.n

    def desaveugler(self, sig_aveugle: int):
        s = (sig_aveugle * pow(self.r, -1, self.n)) % self.n
        return (self.serial, s)


class Agregateur:
    """Accepte UNE contribution par token valide ; partition par epoque."""
    def __init__(self, n: int, e: int):
        self.n, self.e = n, e
        self.depenses = {}
        self.cohortes = {}

    def contribuer(self, epoque: str, token, valeur):
        serial, s = token
        if pow(s, self.e, self.n) != _fdh(serial + epoque.encode(), self.n):
            raise ValueError("REFUS: signature de token invalide")
        brules = self.depenses.setdefault(epoque, set())
        if serial in brules:
            raise PermissionError("REFUS: double depense detectee")
        brules.add(serial)
        self.cohortes.setdefault(epoque, []).append(valeur)
        return True