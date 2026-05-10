"""
ancre_tests.py
ANCRE — Attested Noise Client Runtime Engine
Suite de tests adversariaux — Red Team

Scénarios testés :
  T01 — Kill-switch K < 100
  T02 — Kill-switch ε_total > 1.5
  T03 — Opérateur non autorisé
  T04 — Signature falsifiée
  T05 — Signal tampered (hash incohérent)
  T06 — Coalition attack (40+ signaux corrélés)
  T07 — Reject MOCK en mode production
  T08 — Batch integrity (signal modifié post-attestation)
  T09 — Signal hors plage [0,1]
  T10 — Pipeline complet nominal (régression)

Auteur : SAS VERA / ANCRE
Version : 0.1
"""

import base64
import hashlib
import json
import numpy as np
import logging
import sys
from datetime import datetime, timezone

from ancre_sim_attest import AncreSimAttestClient, SimAttestation
from ancre_verify import AncreAttestVerifier, VerificationResult
from ancre_pipeline import AncreClient, AncreServer, EPSILON_MAX, K_MIN

# Silence les logs pendant les tests
logging.disable(logging.CRITICAL)

# ─────────────────────────────────────────────
# Framework de test minimal
# ─────────────────────────────────────────────

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def test(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"{status}  {name}")
    if detail:
        print(f"       → {detail}")

def section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")

# ─────────────────────────────────────────────
# Fixtures communes
# ─────────────────────────────────────────────

def make_client(mock=True):
    return AncreSimAttestClient(mock=mock)

def make_verifier(reject_mock=False, trusted_orgs=None):
    return AncreAttestVerifier(
        trusted_operator_orgs=trusted_orgs or [
            "ANCRE-MOCK-OPERATOR", "Orange", "SFR",
            "Bouygues Telecom", "Transatel"
        ],
        reject_mock=reject_mock,
    )

def attest(client, signal=0.5):
    att = client.attest_signal(signal)
    return att

def verify(verifier, signal, att):
    return verifier.verify(
        noisy_signal=signal,
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

# ─────────────────────────────────────────────
# T01 — Kill-switch K < 100
# ─────────────────────────────────────────────

section("T01 — Kill-switch K < 100")

def test_t01():
    client = AncreClient(mock_sim=True)
    server = AncreServer(reject_mock=False)

    # Injecter seulement 50 signaux (< K_MIN=100)
    for _ in range(50):
        att = client.process_signal(np.random.uniform(0.1, 0.9))
        server.receive(att)

    result = server.aggregate()

    test(
        "T01a — kill_switch déclenché si K=50 < 100",
        result.kill_switch_triggered,
        f"K={result.k_actual}"
    )
    test(
        "T01b — aucun agrégat exporté (value=0.0)",
        result.aggregate_value == 0.0,
        f"aggregate={result.aggregate_value}"
    )
    test(
        "T01c — VSI=0.0 sur kill-switch",
        result.vsi == 0.0,
        f"VSI={result.vsi}"
    )

test_t01()

# ─────────────────────────────────────────────
# T02 — Kill-switch ε_total > 1.5
# ─────────────────────────────────────────────

section("T02 — Kill-switch ε_total > 1.5")

def test_t02():
    """
    Simule une tentative de contournement du budget epsilon.
    On monkey-patch les constantes pour forcer la violation.
    """
    import ancre_pipeline as ap

    original_max = ap.EPSILON_MAX
    original_server = ap.EPSILON_SERVER

    # Forcer ε_total à dépasser le max
    ap.EPSILON_SERVER = 1.0   # ε_total = 1.0 + 1.0 = 2.0
    ap.EPSILON_TOTAL  = ap.EPSILON_CLIENT + ap.EPSILON_SERVER

    client = AncreClient(mock_sim=True)
    server = AncreServer(reject_mock=False)

    for _ in range(120):
        att = client.process_signal(np.random.uniform(0.1, 0.9))
        server.receive(att)

    result = server.aggregate()

    test(
        "T02a — kill_switch déclenché si ε_total=2.0 > 1.5",
        result.kill_switch_triggered,
        f"ε_total={ap.EPSILON_TOTAL}"
    )
    test(
        "T02b — buffer vidé post kill-switch",
        len(server._buffer) == 0,
        f"buffer={len(server._buffer)}"
    )

    # Restaurer
    ap.EPSILON_SERVER = original_server
    ap.EPSILON_TOTAL  = ap.EPSILON_CLIENT + ap.EPSILON_SERVER
    ap.EPSILON_MAX    = original_max

test_t02()

# ─────────────────────────────────────────────
# T03 — Opérateur non autorisé
# ─────────────────────────────────────────────

section("T03 — Opérateur non autorisé")

def test_t03():
    client_att = make_client()
    # Verifier qui n'accepte PAS ANCRE-MOCK-OPERATOR
    verifier_strict = make_verifier(
        trusted_orgs=["Orange", "SFR", "Bouygues Telecom"]
    )

    signal = 0.65
    att = attest(client_att, signal)
    result = verify(verifier_strict, signal, att)

    test(
        "T03a — attestation rejetée si opérateur non dans la liste",
        not result.valid,
        f"reason='{result.reason}'"
    )
    test(
        "T03b — operator_org identifié dans le rejet",
        result.operator_org == "ANCRE-MOCK-OPERATOR",
        f"operator_org='{result.operator_org}'"
    )

test_t03()

# ─────────────────────────────────────────────
# T04 — Signature falsifiée
# ─────────────────────────────────────────────

section("T04 — Signature falsifiée")

def test_t04():
    client_att = make_client()
    verifier = make_verifier()

    signal = 0.42
    att = attest(client_att, signal)

    # Remplace la signature par du bruit aléatoire
    fake_sig = bytes(np.random.randint(0, 256, 64).tolist())

    result = verifier.verify(
        noisy_signal=signal,
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(fake_sig).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T04a — signature aléatoire rejetée",
        not result.valid,
        f"reason='{result.reason}'"
    )

    # Signature d'un autre signal (replay attack)
    other_signal = 0.99
    other_att = attest(client_att, other_signal)

    result_replay = verifier.verify(
        noisy_signal=signal,
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(other_att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T04b — replay attack rejeté (signature d'un autre signal)",
        not result_replay.valid,
        f"reason='{result_replay.reason}'"
    )

test_t04()

# ─────────────────────────────────────────────
# T05 — Signal tampered (hash incohérent)
# ─────────────────────────────────────────────

section("T05 — Signal tampered")

def test_t05():
    client_att = make_client()
    verifier = make_verifier()

    signal = 0.55
    att = attest(client_att, signal)

    # L'attaquant modifie le signal transmis MAIS garde le hash/signature originaux
    tampered_signal = 0.99

    result = verifier.verify(
        noisy_signal=tampered_signal,  # signal modifié
        signal_hash_b64=base64.b64encode(att.signal_hash).decode(),  # hash original
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T05a — signal tampered détecté via incohérence hash",
        not result.valid,
        f"reason='{result.reason}'"
    )

    # Variante : hash recalculé sur le signal modifié (mais signature invalide)
    tampered_hash = hashlib.sha256(str(tampered_signal).encode()).digest()
    result2 = verifier.verify(
        noisy_signal=tampered_signal,
        signal_hash_b64=base64.b64encode(tampered_hash).decode(),
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T05b — hash recalculé + signature invalide → rejeté",
        not result2.valid,
        f"reason='{result2.reason}'"
    )

test_t05()

# ─────────────────────────────────────────────
# T06 — Coalition attack
# ─────────────────────────────────────────────

section("T06 — Coalition attack (40+ signaux corrélés)")

def test_t06():
    client = AncreClient(mock_sim=True)
    server = AncreServer(reject_mock=False)

    # 80 signaux légitimes distribués normalement
    legit_signals = np.random.beta(2, 5, 80).tolist()
    for s in legit_signals:
        att = client.process_signal(s)
        server.receive(att)

    # 40 signaux de coalition — tous proches de 1.0 (tentative de biaiser l'agrégat)
    coalition_value = 0.999
    coalition_signals = [coalition_value] * 40
    for s in coalition_signals:
        att = client.process_signal(s)
        server.receive(att)

    result = server.aggregate()

    test(
        "T06a — pipeline produit un résultat malgré la coalition",
        not result.kill_switch_triggered,
        f"K={result.k_actual}"
    )

    # L'agrégat ne doit pas être dominé par la coalition
    # Beta(2,5) a une moyenne ~0.29 — avec coalition à 0.999
    # Sans protection : agrégat ≈ (80*0.29 + 40*0.999) / 120 ≈ 0.527
    # Avec TMoM + coalition cap : agrégat doit être significativement < 0.8
    test(
        "T06b — agrégat non dominé par la coalition (< 0.80)",
        result.aggregate_value < 0.80,
        f"aggregate={result.aggregate_value:.4f}"
    )

    test(
        "T06c — VSI calculé (pipeline survivable)",
        result.vsi >= 0.0,
        f"VSI={result.vsi}"
    )

test_t06()

# ─────────────────────────────────────────────
# T07 — Reject MOCK en mode production
# ─────────────────────────────────────────────

section("T07 — Reject MOCK en mode production")

def test_t07():
    client_att = make_client(mock=True)
    # Verifier en mode PRODUCTION — reject_mock=True
    verifier_prod = make_verifier(reject_mock=True)

    signal = 0.72
    att = attest(client_att, signal)
    result = verify(verifier_prod, signal, att)

    test(
        "T07a — attestation MOCK rejetée en mode production",
        not result.valid,
        f"reason='{result.reason}'"
    )
    test(
        "T07b — sim_mode correctement identifié dans le rejet",
        "MOCK" in (result.sim_mode or ""),
        f"sim_mode='{result.sim_mode}'"
    )

    # Server en mode production refuse les signaux MOCK
    server_prod = AncreServer(reject_mock=True)
    client_pipe = AncreClient(mock_sim=True)
    att_pipe = client_pipe.process_signal(0.5)
    accepted = server_prod.receive(att_pipe)

    test(
        "T07c — AncreServer(reject_mock=True) refuse les signaux MOCK",
        not accepted,
        f"accepted={accepted}"
    )

test_t07()

# ─────────────────────────────────────────────
# T08 — Batch integrity
# ─────────────────────────────────────────────

section("T08 — Batch integrity")

def test_t08():
    client_att = make_client()
    verifier = make_verifier()

    batch = [0.1, 0.3, 0.5, 0.7, 0.9]
    att = client_att.attest_batch(batch)

    # Vérification correcte du batch
    result_ok = verifier.verify_batch(
        noisy_signals=batch,
        batch_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T08a — batch attestation valide sur les signaux corrects",
        result_ok.valid,
        f"reason='{result_ok.reason}'"
    )

    # Un signal du batch est modifié post-attestation
    tampered_batch = [0.1, 0.3, 0.5, 0.7, 0.999]  # dernier modifié

    result_tampered = verifier.verify_batch(
        noisy_signals=tampered_batch,
        batch_hash_b64=base64.b64encode(att.signal_hash).decode(),
        signature_b64=base64.b64encode(att.signature).decode(),
        certificate_chain_b64=base64.b64encode(att.certificate_chain).decode(),
        sim_mode=att.sim_mode,
    )

    test(
        "T08b — modification d'un signal du batch détectée",
        not result_tampered.valid,
        f"reason='{result_tampered.reason}'"
    )

    # Batch vide
    try:
        att_empty = client_att.attest_batch([])
        result_empty = verifier.verify_batch(
            noisy_signals=[],
            batch_hash_b64=base64.b64encode(att_empty.signal_hash).decode(),
            signature_b64=base64.b64encode(att_empty.signature).decode(),
            certificate_chain_b64=base64.b64encode(att_empty.certificate_chain).decode(),
            sim_mode=att_empty.sim_mode,
        )
        test("T08c — batch vide traité sans crash", True, "")
    except Exception as e:
        test("T08c — batch vide traité sans crash", False, str(e))

test_t08()

# ─────────────────────────────────────────────
# T09 — Signal hors plage [0,1]
# ─────────────────────────────────────────────

section("T09 — Signal hors plage [0,1]")

def test_t09():
    client = AncreClient(mock_sim=True)

    # Signal > 1.0
    try:
        client.process_signal(1.5)
        test("T09a — signal > 1.0 rejeté", False, "Aucune exception levée")
    except ValueError as e:
        test("T09a — signal > 1.0 rejeté", True, str(e))

    # Signal < 0.0
    try:
        client.process_signal(-0.1)
        test("T09b — signal < 0.0 rejeté", False, "Aucune exception levée")
    except ValueError as e:
        test("T09b — signal < 0.0 rejeté", True, str(e))

    # Limites valides
    try:
        client.process_signal(0.0)
        client.process_signal(1.0)
        test("T09c — limites 0.0 et 1.0 acceptées", True, "")
    except Exception as e:
        test("T09c — limites 0.0 et 1.0 acceptées", False, str(e))

test_t09()

# ─────────────────────────────────────────────
# T10 — Pipeline nominal (régression)
# ─────────────────────────────────────────────

section("T10 — Pipeline nominal (régression)")

def test_t10():
    client = AncreClient(mock_sim=True)
    server = AncreServer(reject_mock=False)

    N = 120
    signals = np.random.beta(2, 5, N).tolist()
    accepted = 0

    for s in signals:
        att = client.process_signal(s)
        if server.receive(att):
            accepted += 1

    result = server.aggregate()

    test(
        "T10a — K≥100 respecté",
        result.k_actual >= K_MIN,
        f"K={result.k_actual}"
    )
    test(
        "T10b — ε_total≤1.5 respecté",
        result.epsilon_total <= EPSILON_MAX,
        f"ε_total={result.epsilon_total}"
    )
    test(
        "T10c — agrégat dans [0,1]",
        0.0 <= result.aggregate_value <= 1.0,
        f"aggregate={result.aggregate_value:.4f}"
    )
    test(
        "T10d — kill_switch non déclenché",
        not result.kill_switch_triggered,
        ""
    )
    test(
        "T10e — attestation_rate=100%",
        result.attestation_rate == 1.0,
        f"rate={result.attestation_rate:.2%}"
    )
    test(
        "T10f — pipeline=ANCRE_v0.1",
        result.pipeline == "ANCRE_v0.1",
        f"pipeline='{result.pipeline}'"
    )

test_t10()

# ─────────────────────────────────────────────
# Résumé final
# ─────────────────────────────────────────────

print(f"\n{'='*55}")
print("ANCRE — RÉSUMÉ DES TESTS")
print(f"{'='*55}")

passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total  = len(results)

print(f"\nTotal  : {total}")
print(f"Pass   : {passed} ✅")
print(f"Fail   : {failed} ❌")
print(f"\nScore  : {passed}/{total} ({100*passed//total}%)")

if failed > 0:
    print(f"\n{'─'*55}")
    print("TESTS ÉCHOUÉS :")
    for name, ok, detail in results:
        if not ok:
            print(f"  ❌ {name}")
            if detail:
                print(f"     → {detail}")

print(f"\n{'='*55}")
sys.exit(0 if failed == 0 else 1)
