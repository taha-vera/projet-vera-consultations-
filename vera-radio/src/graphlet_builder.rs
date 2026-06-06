#[derive(Debug, Clone)]
pub struct AudioFeatures {
    pub energy:    f64,
    pub variance:    f64,
    pub mean: f64,
    pub zcr: f64,
}

#[derive(Debug)]
pub struct RadioGraphlet {
    pub aggregated_value: f64,
    pub count:            usize,
}

impl RadioGraphlet {
    pub fn from_features(f: AudioFeatures) -> Result<Self, String> {
        let values = [f.energy, f.variance, f.mean, f.zcr];
        for v in values {
            if !v.is_finite() {
                return Err(format!("non-finite feature: {v}"));
            }
        }
        let sum: f64 = values.iter().sum();
        Ok(Self { aggregated_value: sum / values.len() as f64, count: values.len() })
    }
}
