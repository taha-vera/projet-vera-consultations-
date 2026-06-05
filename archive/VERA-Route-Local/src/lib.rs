pub mod inference;
pub mod fallback;
pub mod metrics;
pub mod tee_hooks;
pub mod error;

pub use inference::{InferenceEngine, ClassificationResult};
pub use metrics::LatencyMetrics;
pub use error::Result;

#[derive(Debug, Clone)]
pub struct RouteLocalConfig {
    pub model_path: String,
    pub use_npu: bool,
    pub fallback_on_error: bool,
}

impl Default for RouteLocalConfig {
    fn default() -> Self {
        Self {
            model_path: "./models/gemma2_2b.gguf".to_string(),
            use_npu: true,
            fallback_on_error: true,
        }
    }
}
