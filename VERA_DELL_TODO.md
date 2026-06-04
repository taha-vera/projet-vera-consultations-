# VERA Dell — Next Steps

## Priority 1: Real FmStream (vera-radio v0.3)

Replace stub in vera-radio/src/capture/fm.rs with real HTTP stream:

1. Add dependencies to vera-radio/Cargo.toml:
   - ureq = "2" (HTTP stream)
   - symphonia = { version = "0.5", features = ["aac"] } (audio decode)

2. Implement FmStream::next_chunk():
   - Connect to http://icecast.radiofrance.fr/fip-hifi.aac
   - Decode AAC frames
   - Return PCM samples as Vec<f32>

3. Connect to rustfft (already in vera-radio)
   - FFT on PCM chunk
   - Extract bass/mid/treble energy

4. Full pipeline:
   FIP stream → PCM → FFT → vera-radio-sdk ingest → DP export → vera-client-sdk purchase

## Priority 2: Run on Dell
   cargo build --release --workspace
   bash vera_demo_realtime.sh

## Expected output:
   Real FIP Radio signal → ExportedPattern with DP guarantee → Purchase receipt 70/30
