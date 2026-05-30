pub mod genre;
pub mod tempo;
pub mod language;
use crate::graphlet_builder::AudioFeatures;

pub fn extract_features(signal: &str) -> Result<AudioFeatures, String> {
    let g = genre::detect_genre(signal);
    let t = tempo::detect_tempo(signal);
    let l = language::detect_language(signal);
    for (name, val) in [("genre", g), ("tempo", t), ("language", l)] {
        if !val.is_finite() {
            return Err(format!("non-finite feature '{}': {}", name, val));
        }
    }
    Ok(AudioFeatures { genre: g, tempo: t, language: l })
}
