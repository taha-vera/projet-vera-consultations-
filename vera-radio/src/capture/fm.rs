use std::io::{Read, Cursor};
use symphonia::core::audio::SampleBuffer;
use symphonia::core::codecs::DecoderOptions;
use symphonia::core::formats::FormatOptions;
use symphonia::core::io::MediaSourceStream;
use symphonia::core::meta::MetadataOptions;
use symphonia::core::probe::Hint;

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
        // 1. Capture raw AAC bytes
        let response = ureq::get(&self.url)
            .timeout(std::time::Duration::from_secs(10))
            .call()
            .ok()?;

        let mut raw = vec![0u8; 131072]; // 128KB
        let n = response.into_reader().read(&mut raw).ok()?;
        if n == 0 { return None; }
        raw.truncate(n);

        // 2. Decode AAC → PCM via symphonia
        let cursor = Cursor::new(raw);
        let mss = MediaSourceStream::new(Box::new(cursor), Default::default());

        let mut hint = Hint::new();
        hint.mime_type("audio/aac");

        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &FormatOptions::default(), &MetadataOptions::default())
            .ok()?;

        let mut format = probed.format;
        let track = format.tracks().first()?;
        let track_id = track.id;

        let mut decoder = symphonia::default::get_codecs()
            .make(&track.codec_params, &DecoderOptions::default())
            .ok()?;

        let mut pcm_bytes: Vec<u8> = Vec::new();

        // Decode up to 4 packets
        for _ in 0..4 {
            let packet = match format.next_packet() {
                Ok(p) if p.track_id() == track_id => p,
                _ => break,
            };
            let decoded = match decoder.decode(&packet) {
                Ok(d) => d,
                Err(_) => break,
            };
            let spec = *decoded.spec();
            let mut sample_buf = SampleBuffer::<f32>::new(decoded.capacity() as u64, spec);
            sample_buf.copy_interleaved_ref(decoded);

            // Convert f32 samples to bytes — then zeroize
            for sample in sample_buf.samples() {
                pcm_bytes.extend_from_slice(&sample.to_le_bytes());
            }
        }

        if pcm_bytes.is_empty() { return None; }

        // 3. Raw PCM will be zeroized by vera-spine after feature extraction
        Some(pcm_bytes)
    }
}

impl Default for FmStream {
    fn default() -> Self { Self::new() }
}
