pub struct FmStream;
impl FmStream {
    pub fn new() -> Self { Self }
    pub fn next_chunk(&self) -> Option<String> {
        Some("afrobeat saxophone electronic".to_string())
    }
}
impl Default for FmStream { fn default() -> Self { Self } }
