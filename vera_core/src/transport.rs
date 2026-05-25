pub struct TransportMessage {
    pub payload: Vec<u8>,
}

impl TransportMessage {
    pub fn new(payload: Vec<u8>) -> Self {
        Self { payload }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transport_message_holds_payload() {
        let m = TransportMessage::new(vec![1,2,3]);
        assert_eq!(m.payload, vec![1,2,3]);
    }
}
