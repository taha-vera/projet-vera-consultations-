pub struct TEEBridge;

impl TEEBridge {
    pub async fn new() -> crate::error::Result<Self> {
        Ok(Self)
    }
}
