#[cfg(test)]
mod tests {
    use vera_core::vera_sevsnssp::SEVSNPReport;

    #[test]
    fn test_sevsnssp_complete() {
        let mut buf = vec![0u8; 0x4A0];
        buf[0x90..0x90+48].copy_from_slice(&[1u8; 48]);
        buf[0x08..0x10].copy_from_slice(&0x1234567890ABCDEFu64.to_le_bytes());
        
        let report = SEVSNPReport::parse_complete(&buf).unwrap();
        assert_eq!(report.version, 0);
        assert_eq!(report.policy, 0x1234567890ABCDEFu64);
        println!("✅ SEV-SNP Complete Parser: OK");
    }

    #[test]
    fn test_attestation_binding() {
        let mut buf = vec![0u8; 0x4A0];
        let measurement = [5u8; 48];
        buf[0x90..0x90+48].copy_from_slice(&measurement);
        
        let report = SEVSNPReport::parse_complete(&buf).unwrap();
        assert!(report.verify_measurement(&measurement).is_ok());
        println!("✅ Attestation Binding: OK");
    }
}
