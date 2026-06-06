pub mod energy;
pub mod variance;
pub mod mean;
pub mod zcr;
use crate::graphlet_builder::AudioFeatures;

pub fn extract_features(signal: &[u8]) -> Result<AudioFeatures, String> {
    let g = energy::detect_energy(signal);
    let t = variance::detect_variance(signal);
    let l = mean::detect_mean(signal);
    let z = zcr::detect_zcr(signal);
    for (name, val) in [("energy", g), ("variance", t), ("mean", l), ("zcr", z)] {
        if !val.is_finite() {
            return Err(format!("non-finite feature '{}': {}", name, val));
        }
    }
    Ok(AudioFeatures { energy: g, variance: t, mean: l, zcr: z })
}
