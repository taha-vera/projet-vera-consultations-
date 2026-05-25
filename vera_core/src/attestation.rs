pub struct AttestationReport {
    pub valid: bool,
}

impl AttestationReport {
    pub fn verify(&self) -> bool {
        self.valid
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn attestation_verifies_true() {
        let r = AttestationReport { valid: true };
        assert!(r.verify());
    }

    #[test]
    fn attestation_verifies_false() {
        let r = AttestationReport { valid: false };
        assert!(!r.verify());
    }
}
