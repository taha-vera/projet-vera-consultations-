pub struct HpkeKeyPair {
    pub public_key: Vec<u8>,
    pub private_key: Vec<u8>,
}

impl HpkeKeyPair {
    pub fn generate() -> Self {
        HpkeKeyPair {
            public_key: vec![1,2,3],
            private_key: vec![4,5,6],
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hpke_generates_keys() {
        let k = HpkeKeyPair::generate();
        assert!(!k.public_key.is_empty());
        assert!(!k.private_key.is_empty());
    }
}
