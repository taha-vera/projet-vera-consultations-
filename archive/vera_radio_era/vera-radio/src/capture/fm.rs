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
        Self { url: "http://icecast.radiofrance.fr/fip-hifi.aac".to_string() }
    }
    pub fn with_url(url: &str) -> Self {
        Self { url: url.to_string() }
    }
    pub fn next_chunk(&self) -> Option<Vec<u8>> {
        let response = ureq::get(&self.url)
            .timeout(std::time::Duration::from_secs(10))
            .call()
            .ok()?;
        let mut raw = Vec::with_capacity(131072);
        response.into_reader().take(131072).read_to_end(&mut raw).ok()?;
        if raw.is_empty() { return None; }

        let cursor = Cursor::new(raw);
        let mss = MediaSourceStream::new(Box::new(cursor), Default::default());
        let mut hint = Hint::new();
        hint.mime_type("audio/aac");
        let probed = symphonia::default::get_probe()
            .format(&hint, mss, &FormatOptions::default(), &MetadataOptions::default())
            .ok()?;
        let mut format = probed.format;
        let track_id = format.tracks().first()?.id;
        let codec_params = format.tracks().first()?.codec_params.clone();
        let mut decoder = symphonia::default::get_codecs()
            .make(&codec_params, &DecoderOptions::default())
            .ok()?;

        let mut pcm_bytes: Vec<u8> = Vec::new();
        loop {
            let packet = match format.next_packet() {
                Ok(p) => p,
                Err(_) => break,
            };
            if packet.track_id() != track_id { continue; }
            let decoded = match decoder.decode(&packet) {
                Ok(d) => d,
                Err(_) => continue,
            };
            let spec = *decoded.spec();
            let mut sample_buf = SampleBuffer::<f32>::new(decoded.capacity() as u64, spec);
            sample_buf.copy_interleaved_ref(decoded);
            for sample in sample_buf.samples() {
                pcm_bytes.extend_from_slice(&sample.to_le_bytes());
            }
        }
        if pcm_bytes.is_empty() { return None; }
        Some(pcm_bytes)
    }
}

impl Default for FmStream {
    fn default() -> Self { Self::new() }
}
