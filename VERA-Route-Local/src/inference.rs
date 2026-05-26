use crate::error::Result;
use crate::fallback::CPUFallback;
use std::sync::Arc;
use parking_lot::RwLock;

#[derive(Debug, Clone)]
pub struct ClassificationResult {
    pub text: String,
    pub sensitivity_score: f32,
    pub success: bool,
    pub used_npu: bool,
}

pub struct InferenceEngine {
    cpu_fallback: Arc<RwLock<Option<CPUFallback>>>,
}

impl InferenceEngine {
    pub async fn new(_config: &crate::RouteLocalConfig) -> Result<Self> {
        Ok(Self {
            cpu_fallback: Arc::new(RwLock::new(CPUFallback::new().ok())),
        })
    }

    pub async fn classify(&self, input: &str) -> Result<ClassificationResult> {
        if let Some(ref fb) = *self.cpu_fallback.read() {
            fb.classify(input).await
        } else {
            Err(crate::error::RouteLocalError::InferenceFailed("No fallback".into()))
        }
    }
}
