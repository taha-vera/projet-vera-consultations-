#[derive(Debug, Clone)]
pub struct AudioFeatures {
    pub genre:    f64,
    pub tempo:    f64,
    pub language: f64,
}

#[derive(Debug)]
pub struct RadioGraphlet {
    pub aggregated_value: f64,
    pub count:            usize,
}

impl RadioGraphlet {
    pub fn from_features(f: AudioFeatures) -> Result<Self, String> {
        let values = [f.genre, f.tempo, f.language];
        for v in values {
            if !v.is_finite() {
                return Err(format!("non-finite feature: {v}"));
            }
        }
        let sum: f64 = values.iter().sum();
        Ok(Self { aggregated_value: sum / values.len() as f64, count: values.len() })
    }
}
