use thiserror::Error;
pub type Result<T> = std::result::Result<T, RouteLocalError>;

#[derive(Error, Debug)]
pub enum RouteLocalError {
    #[error("Inference failed: {0}")]
    InferenceFailed(String),
    #[error("NPU not available")]
    NPUUnavailable(String),
    #[error("Model loading failed: {0}")]
    ModelLoadError(String),
    #[error("TEE error: {0}")]
    TEEError(String),
}
