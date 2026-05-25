pub struct VeraClient {
    pub connected: bool,
}

impl VeraClient {
    pub fn new() -> Self {
        Self { connected: false }
    }

    pub fn connect(&mut self) {
        self.connected = true;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn client_starts_disconnected() {
        let c = VeraClient::new();
        assert!(!c.connected);
    }

    #[test]
    fn client_connects() {
        let mut c = VeraClient::new();
        c.connect();
        assert!(c.connected);
    }
}
