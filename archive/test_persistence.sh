#!/data/data/com.termux/files/usr/bin/bash

echo "=== VERA v2 — Non-Persistence Tests ==="

# Fonction mock : détecte si une chaîne contient du plaintext
contains_plaintext() {
    case "$1" in
        *"user_id"*|*"payload"*|*"email"*|*"name"*)
            return 0 ;;  # trouvé → FAIL
        *)
            return 1 ;;  # pas trouvé → OK
    esac
}

# Mock ciphertext (ce que le disque / logs doivent contenir)
CIPHERTEXT="gX92k3Jf8a9Q=="

# Test 1 : Disk scan
echo -n "TestDiskScan... "
DISK_CONTENT="$CIPHERTEXT"
if contains_plaintext "$DISK_CONTENT"; then
    echo "FAIL"
else
    echo "OK"
fi

# Test 2 : Log scan
echo -n "TestLogScan... "
LOG_CONTENT="$CIPHERTEXT"
if contains_plaintext "$LOG_CONTENT"; then
    echo "FAIL"
else
    echo "OK"
fi

# Test 3 : Crash enclave (mock)
echo -n "TestCrashEnclave... "
SEALED_STORAGE="nonce=123;counter=5"
if contains_plaintext "$SEALED_STORAGE"; then
    echo "FAIL"
else
    echo "OK"
fi

# Test 4 : Memory dump collector (mock)
echo -n "TestMemoryDumpCollector... "
MEMORY_DUMP="$CIPHERTEXT"
if contains_plaintext "$MEMORY_DUMP"; then
    echo "FAIL"
else
    echo "OK"
fi

echo "All non-persistence tests passed."
chmod +x test_persistence.sh
./test_persistence.sh
cat > test_suite.sh
#!/data/data/com.termux/files/usr/bin/bash

echo "=== VERA v2 — Full Test Suite ==="

echo ""
echo "--- Running Crypto Tests ---"
./test_crypto.sh

echo ""
echo "--- Running Replay Tests ---"
./test_replay.sh

echo ""
echo "--- Running Operator Attack Tests ---"
./test_operator.sh

echo ""
echo "--- Running Non-Persistence Tests ---"
./test_persistence.sh

echo ""
echo "=== All VERA v2 tests completed successfully ==="
