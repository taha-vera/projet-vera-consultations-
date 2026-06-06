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
        let mut raw = vec![0u8; 65536]; // 64KB AAC
        let n = reader.read(&mut raw).ok()?;
        if n == 0 { return None; }
        raw.truncate(n);

        // Convert AAC bytes to pseudo-PCM energy samples
        // Each byte normalized to [-1.0, 1.0] float32
        let pcm: Vec<u8> = raw.iter()
            .map(|&b| {
                let sample = (b as f32 / 128.0) - 1.0;
                sample.to_le_bytes()
            })
            .flatten()
            .collect();

        Some(pcm)
    }
}

impl Default for FmStream {
    fn default() -> Self { Self::new() }
}
