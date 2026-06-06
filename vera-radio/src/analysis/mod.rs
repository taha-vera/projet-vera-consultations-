pub mod energy;
pub mod variance;
pub mod mean;
use crate::graphlet_builder::AudioFeatures;

pub fn extract_features(signal: &[u8]) -> Result<AudioFeatures, String> {
    let g = energy::detect_energy(signal);
    let t = variance::detect_variance(signal);
    let l = mean::detect_mean(signal);
    for (name, val) in [("genre", g), ("tempo", t), ("language", l)] {
        if !val.is_finite() {
            return Err(format!("non-finite feature '{}': {}", name, val));
        }
    }
    Ok(AudioFeatures { energy: g, variance: t, mean: l })
}
