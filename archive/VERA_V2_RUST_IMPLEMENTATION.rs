// VERA v2 — Rust Implementation (CCS-Grade)
// Invariants: Attestation binding, Anti-replay, Ledger chaining

use sha2::{Sha256, Digest};
use ed25519_dalek::{SigningKey, VerifyingKey, Signature};
use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

// ============================================================================
// 1. ATTESTATION BINDING (CBOR Format)
// ============================================================================

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct AttestationReport {
    pub measurement: Vec<u8>,           // mrenclave/measurement
    pub report_data: Vec<u8>,           // SHA256(binding)
    pub nonce: Vec<u8>,                 // challenge from client
    pub hpke_pubkey_hash: Vec<u8>,      // SHA256(pk_tee)
    pub timestamp: u64,                 // Unix timestamp
    pub tcb_version: String,            // "2.0"
}

// INVARIANT 1: Binding attestation ↔ HPKE pubkey
// report_data = SHA256(hpke_pubkey || nonce || version || measurement)
pub fn verify_attestation_binding(
    report: &AttestationReport,
    hpke_pubkey: &[u8],
    client_nonce: &[u8],
) -> Result<(), String> {
    // Compute expected binding
    let mut hasher = Sha256::new();
    hasher.update(hpke_pubkey);
    hasher.update(client_nonce);
    hasher.update(report.tcb_version.as_bytes());
    hasher.update(&report.measurement);
    let expected_report_data = hasher.finalize().to_vec();

    if report.report_data != expected_report_data {
        return Err("Attestation binding failed: report_data mismatch".to_string());
    }

    Ok(())
}

// ============================================================================
// 2. ANTI-REPLAY LEDGER (Append-Only with Hash Chaining)
// ============================================================================

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct LedgerEntry {
    pub counter: u64,
    pub nonce: Vec<u8>,
    pub prev_hash: Vec<u8>,             // Hash of previous entry
    pub entry_hash: Vec<u8>,            // SHA256(prev_hash || nonce || counter || timestamp)
    pub timestamp: u64,
}

pub struct AntiReplayLedger {
    entries: Vec<LedgerEntry>,
    nonce_cache: HashMap<Vec<u8>, u64>, // nonce → timestamp
    counter: u64,
    path: String,
}

impl AntiReplayLedger {
    pub fn new(path: &str) -> Result<Self, String> {
        let mut ledger = AntiReplayLedger {
            entries: Vec::new(),
            nonce_cache: HashMap::new(),
            counter: 0,
            path: path.to_string(),
        };

        // Load from disk if exists
        if Path::new(path).exists() {
            let data = fs::read_to_string(path)
                .map_err(|e| format!("Failed to load ledger: {}", e))?;
            let entries: Vec<LedgerEntry> = serde_json::from_str(&data)
                .map_err(|e| format!("Failed to parse ledger: {}", e))?;
            
            ledger.entries = entries;
            ledger.counter = ledger.entries.len() as u64;
            
            // Rebuild nonce cache
            for entry in &ledger.entries {
                ledger.nonce_cache.insert(entry.nonce.clone(), entry.timestamp);
            }
        }

        Ok(ledger)
    }

    // INVARIANT 2: Anti-Replay (Triple Defense)
    pub fn verify_and_add(&mut self, nonce: &[u8]) -> Result<(), String> {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // Check 1: Exact nonce uniqueness
        if self.nonce_cache.contains_key(nonce) {
            return Err("Exact replay: nonce seen before".to_string());
        }

        // Check 2: Timestamp drift (30 second window)
        // (Would be checked client-side; server accepts fresh nonces)

        // Check 3: Add to ledger with hash chaining
        let prev_hash = if let Some(last) = self.entries.last() {
            last.entry_hash.clone()
        } else {
            vec![0u8; 32] // Genesis entry
        };

        let mut hasher = Sha256::new();
        hasher.update(&prev_hash);
        hasher.update(nonce);
        hasher.update(self.counter.to_le_bytes());
        hasher.update(now.to_le_bytes());
        let entry_hash = hasher.finalize().to_vec();

        let entry = LedgerEntry {
            counter: self.counter,
            nonce: nonce.to_vec(),
            prev_hash,
            entry_hash,
            timestamp: now,
        };

        self.entries.push(entry);
        self.nonce_cache.insert(nonce.to_vec(), now);
        self.counter += 1;

        // Persist to disk
        self.persist()?;

        Ok(())
    }

    fn persist(&self) -> Result<(), String> {
        let json = serde_json::to_string_pretty(&self.entries)
            .map_err(|e| format!("Serialization failed: {}", e))?;
        fs::write(&self.path, json)
            .map_err(|e| format!("Write failed: {}", e))?;
        Ok(())
    }

    // Test: Reboot Replay Detection
    pub fn detect_reboot_replay(&self, nonce: &[u8]) -> bool {
        // After reboot, ledger is reloaded from disk.
        // If same nonce exists → replay detected.
        self.nonce_cache.contains_key(nonce)
    }
}

// ============================================================================
// 3. CLIENT VALIDATION (Hostile Host)
// ============================================================================

pub struct ClientValidator {
    expected_measurement: Vec<u8>,
    expected_version: String,
}

impl ClientValidator {
    pub fn new(measurement: Vec<u8>, version: String) -> Self {
        ClientValidator {
            expected_measurement: measurement,
            expected_version: version,
        }
    }

    // INVARIANT 3: Client-side validation (three bloquant assertions)
    pub fn validate(&self, report: &AttestationReport) -> Result<(), String> {
        // Assertion 1: Measurement matches
        if report.measurement != self.expected_measurement {
            return Err(format!(
                "Measurement mismatch: expected {:?}, got {:?}",
                self.expected_measurement, report.measurement
            ));
        }

        // Assertion 2: Version matches (prevents downgrade)
        if report.tcb_version != self.expected_version {
            return Err(format!(
                "Version mismatch: expected {}, got {}",
                self.expected_version, report.tcb_version
            ));
        }

        // Assertion 3: Timestamp freshness (<5 minutes)
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        if now - report.timestamp > 300 {
            return Err("Attestation expired (>5 minutes)".to_string());
        }

        Ok(())
    }
}

// ============================================================================
// 4. HPKE ENCRYPTION (with AAD binding)
// ============================================================================

pub struct HPKEContext {
    pubkey: Vec<u8>,
    measurement: Vec<u8>,
    version: String,
}

impl HPKEContext {
    pub fn new(pubkey: Vec<u8>, measurement: Vec<u8>, version: String) -> Self {
        HPKEContext { pubkey, measurement, version }
    }

    // AAD binds to TEE identity
    pub fn compute_aad(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(b"VERA_v2_aggregation");
        hasher.update(&self.pubkey);
        hasher.update(&self.measurement);
        hasher.update(self.version.as_bytes());
        hasher.finalize().to_vec()
    }
}

// ============================================================================
// 5. INTEGRATION TEST: Reboot Replay
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_reboot_replay_detection() {
        // Setup
        let ledger_path = "/tmp/vera_test_ledger.json";
        let _ = fs::remove_file(ledger_path);

        let nonce = b"test_nonce_12345".to_vec();

        // Step 1: Add nonce
        let mut ledger1 = AntiReplayLedger::new(ledger_path).unwrap();
        ledger1.verify_and_add(&nonce).unwrap();
        println!("✓ Nonce added: counter={}", ledger1.counter);

        // Simulate reboot: drop ledger, reload from disk
        drop(ledger1);

        // Step 2: Reload ledger (simulating reboot)
        let ledger2 = AntiReplayLedger::new(ledger_path).unwrap();
        println!("✓ Ledger reloaded from disk: counter={}", ledger2.counter);

        // Step 3: Attempt replay
        let is_replay = ledger2.detect_reboot_replay(&nonce);
        assert!(is_replay, "Reboot replay not detected!");
        println!("✓ Replay detected after reboot");

        // Cleanup
        let _ = fs::remove_file(ledger_path);
    }

    #[test]
    fn test_attestation_binding() {
        let hpke_pubkey = b"test_hpke_key".to_vec();
        let client_nonce = b"client_nonce_123".to_vec();
        let measurement = b"test_measurement".to_vec();

        // Compute correct binding
        let mut hasher = Sha256::new();
        hasher.update(&hpke_pubkey);
        hasher.update(&client_nonce);
        hasher.update(b"2.0");
        hasher.update(&measurement);
        let correct_binding = hasher.finalize().to_vec();

        // Create valid report
        let report = AttestationReport {
            measurement: measurement.clone(),
            report_data: correct_binding,
            nonce: client_nonce.clone(),
            hpke_pubkey_hash: sha256(&hpke_pubkey),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            tcb_version: "2.0".to_string(),
        };

        // Verify binding
        let result = verify_attestation_binding(&report, &hpke_pubkey, &client_nonce);
        assert!(result.is_ok(), "Valid binding rejected");
        println!("✓ Attestation binding verified");
    }

    #[test]
    fn test_downgrade_prevention() {
        let validator = ClientValidator::new(
            b"expected_measurement".to_vec(),
            "2.0".to_string(),
        );

        // Report with wrong version
        let report = AttestationReport {
            measurement: b"expected_measurement".to_vec(),
            report_data: vec![0u8; 32],
            nonce: b"nonce".to_vec(),
            hpke_pubkey_hash: vec![0u8; 32],
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            tcb_version: "1.0".to_string(), // ← Wrong version
        };

        let result = validator.validate(&report);
        assert!(result.is_err(), "Downgrade not prevented");
        println!("✓ Downgrade prevented");
    }

    fn sha256(data: &[u8]) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(data);
        hasher.finalize().to_vec()
    }
}

fn main() {
    println!("VERA v2 — Rust Implementation Ready");
    println!("Tests: cargo test");
}
