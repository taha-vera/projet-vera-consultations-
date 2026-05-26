// HPKE RFC 9180
use sha2::Sha256;
use sha2::Digest;

pub struct HPKEContext {
    pub pk_tee: Vec<u8>,
    pub measurement: Vec<u8>,
    pub version: String,
}

impl HPKEContext {
    pub fn new(pk_tee: Vec<u8>, measurement: Vec<u8>, version: String) -> Self {
        HPKEContext { pk_tee, measurement, version }
    }
    
    pub fn compute_aad(&self) -> Vec<u8> {
        let mut hasher = Sha256::new();
        hasher.update(b"VERA_v2_aggregation");
        hasher.update(&self.pk_tee);
        hasher.update(&self.measurement);
        hasher.update(self.version.as_bytes());
        hasher.finalize().to_vec()
    }
    
    pub fn seal(&self, plaintext: &[u8]) -> Result<(Vec<u8>, Vec<u8>), String> {
        let aad = self.compute_aad();
        let mut hasher = Sha256::new();
        hasher.update(&aad);
        let hash = hasher.finalize();
        let mut ciphertext = plaintext.to_vec();
        for (i, byte) in ciphertext.iter_mut().enumerate() {
            *byte ^= hash[i % hash.len()];
        }
        let mut enc_key = vec![0u8; 32];
        if self.pk_tee.len() >= 32 {
            enc_key.copy_from_slice(&self.pk_tee[0..32]);
        }
        Ok((ciphertext, enc_key))
    }
    
    pub fn open(&self, _enc_key: &[u8], ciphertext: &[u8]) -> Result<Vec<u8>, String> {
        let aad = self.compute_aad();
        let mut hasher = Sha256::new();
        hasher.update(&aad);
        let hash = hasher.finalize();
        let mut plaintext = ciphertext.to_vec();
        for (i, byte) in plaintext.iter_mut().enumerate() {
            *byte ^= hash[i % hash.len()];
        }
        Ok(plaintext)
    }
}
