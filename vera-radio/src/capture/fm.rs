use std::io::Read;

pub struct FmStream {
    url: String,
}

impl FmStream {
    pub fn new() -> Self {
        Self {
            url: "http://icecast.radiofrance.fr/fip-hifi.aac".to_string(),
        }
    }

    pub fn with_url(url: &str) -> Self {
        Self { url: url.to_string() }
    }

    pub fn next_chunk(&self) -> Option<Vec<u8>> {
        let response = ureq::get(&self.url)
            .timeout(std::time::Duration::from_secs(10))
            .call()
            .ok()?;

        let mut reader = response.into_reader();
        let mut buffer = vec![0u8; 16384]; // 16KB chunk
        let n = reader.read(&mut buffer).ok()?;
        if n == 0 {
            return None;
        }
        buffer.truncate(n);
        Some(buffer)
    }
}

impl Default for FmStream {
    fn default() -> Self {
        Self::new()
    }
}
