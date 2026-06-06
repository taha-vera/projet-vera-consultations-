// Replay + Session
use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct AntiReplayState {
    pub last_counter: u64,
    pub seen_nonces: HashMap<Vec<u8>, u64>,
}

impl AntiReplayState {
    pub fn new() -> Self {
        AntiReplayState {
            last_counter: 0,
            seen_nonces: HashMap::new(),
        }
    }
    
    pub fn verify(&mut self, counter: u64, _timestamp_ms: u64, nonce: &[u8]) -> Result<(), String> {
        if counter <= self.last_counter { return Err("counter not increasing".to_string()); }
        let nonce_key = nonce.to_vec();
        if self.seen_nonces.contains_key(&nonce_key) { return Err("nonce seen".to_string()); }
        self.last_counter = counter;
        self.seen_nonces.insert(nonce_key, 0);
        Ok(())
    }
}

pub struct SessionState {
    pub client_id: String,
    pub pk_tee: Vec<u8>,
    pub measurement: [u8; 48],
}

impl SessionState {
    pub fn new(client_id: String, pk_tee: Vec<u8>, measurement: [u8; 48]) -> Self {
        SessionState { client_id, pk_tee, measurement }
    }
}
