// SEV-SNP Attestation (dual parser)
pub struct SEVSNPReport {
    pub version: u32,
    pub policy: u64,
    pub measurement: [u8; 48],
    pub report_data: [u8; 64],
    pub signature: [u8; 512],
}

impl SEVSNPReport {
    pub fn parse_complete(data: &[u8]) -> Result<Self, String> {
        if data.len() < 0x4A0 { return Err("too small".to_string()); }
        Ok(SEVSNPReport {
            version: u32::from_le_bytes([data[0], data[1], data[2], data[3]]),
            policy: u64::from_le_bytes([data[8], data[9], data[10], data[11], data[12], data[13], data[14], data[15]]),
            measurement: {
                let mut arr = [0u8; 48];
                arr.copy_from_slice(&data[0x90..0x90+48]);
                arr
            },
            report_data: {
                let mut arr = [0u8; 64];
                arr.copy_from_slice(&data[0x50..0x50+64]);
                arr
            },
            signature: {
                let mut arr = [0u8; 512];
                arr.copy_from_slice(&data[0x2A0..0x2A0+512]);
                arr
            },
        })
    }
    
    pub fn parse_simplified(data: &[u8]) -> Result<Self, String> {
        if data.len() < 0x268 { return Err("too small".to_string()); }
        let mut measurement = [0u8; 48];
        measurement.copy_from_slice(&data[0x20..0x20+48]);
        Ok(SEVSNPReport {
            version: 1,
            policy: u64::from_le_bytes([data[0x60], data[0x61], data[0x62], data[0x63], data[0x64], data[0x65], data[0x66], data[0x67]]),
            measurement,
            report_data: [0u8; 64],
            signature: [0u8; 512],
        })
    }
    
    pub fn verify_measurement(&self, expected: &[u8; 48]) -> Result<(), String> {
        if self.measurement == *expected { Ok(()) } else { Err("mismatch".to_string()) }
    }
    
    pub fn extract_hpke_pubkey(&self) -> &[u8] {
        &self.report_data[0..32]
    }
}
