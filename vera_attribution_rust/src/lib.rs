//! vera_attribution — Implementation Rust du flux d'attribution documente
//! dans ATTRIBUTION_FLOW.md, avec garanties memoire via zeroize (au lieu
//! des garanties best-effort du prototype Python equivalent).

pub mod canal_envoi;
pub mod rh_attribution;
pub mod vera_attribution;
pub mod webhook_dedup;

pub use canal_envoi::CanalEnvoiSimule;
pub use rh_attribution::RegistreRH;
pub use vera_attribution::{IdOpaqueEphemere, PoolTokens};
pub use webhook_dedup::{DedupWebhook, ResultatDedup};