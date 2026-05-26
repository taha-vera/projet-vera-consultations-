// Transport
pub trait VeraHttpClient {
    fn post(&self, url: &str, body: &[u8]) -> Result<Vec<u8>, String>;
}

pub struct MockHttpClient;
impl VeraHttpClient for MockHttpClient {
    fn post(&self, _url: &str, body: &[u8]) -> Result<Vec<u8>, String> {
        Ok(body.to_vec())
    }
}
