use crate::graphlet_builder::AudioFeatures;

fn bytes_to_samples(signal: &[u8]) -> Vec<f32> {
    signal
        .chunks_exact(4)
        .map(|b| f32::from_le_bytes([b[0], b[1], b[2], b[3]]))
        .collect()
}

pub fn extract_features(signal: &[u8]) -> Result<AudioFeatures, String> {
    let samples = bytes_to_samples(signal);
    if samples.is_empty() {
        return Err("no PCM samples".to_string());
    }
    let n = samples.len() as f32;
    let mean: f32 = samples.iter().sum::<f32>() / n;
    let energy: f32 = samples.iter().map(|x| x * x).sum::<f32>() / n;
    let variance: f32 = samples.iter().map(|x| (x - mean).powi(2)).sum::<f32>() / n;
    let zcr: f32 = if samples.len() < 2 { 0.0 } else {
        let crossings = samples.windows(2)
            .filter(|w| (w[0] >= 0.0) != (w[1] >= 0.0))
            .count();
        crossings as f32 / (samples.len() - 1) as f32
    };
    for (name, val) in [("energy", energy), ("variance", variance), ("mean", mean), ("zcr", zcr)] {
        if !val.is_finite() {
            return Err(format!("non-finite feature '{}': {}", name, val));
        }
    }
    Ok(AudioFeatures { energy: energy as f64, variance: variance as f64, mean: mean as f64, zcr: zcr as f64 })
}
