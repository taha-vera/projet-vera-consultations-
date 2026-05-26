use crate::error::Result;
use crate::ClassificationResult;
use lazy_static::lazy_static;
use regex::Regex;

lazy_static! {
    static ref NIR_REGEX: Regex = Regex::new(r"\b[1-2]\d{2}\d{10}\d{2}\b").unwrap();
}

pub struct CPUFallback;

impl CPUFallback {
    pub fn new() -> Result<Self> {
        Ok(Self)
    }

    pub async fn classify(&self, input: &str) -> Result<ClassificationResult> {
        let sensitivity = Self::detect_sensitivity(input);
        Ok(ClassificationResult {
            text: input.to_string(),
            sensitivity_score: sensitivity,
            success: true,
            used_npu: false,
        })
    }

    fn detect_sensitivity(input: &str) -> f32 {
        let mut score = 0.0;
        if NIR_REGEX.is_match(input) { score += 0.3; }
        let input_lower = input.to_lowercase();
        if input_lower.contains("sante") { score += 0.2; }
        if input_lower.contains("salaire") { score += 0.2; }
        score.min(1.0)
    }
}
