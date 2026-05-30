use crate::capture::fm::FmStream;
use crate::analysis::extract_features;
use crate::graphlet_builder::RadioGraphlet;
use crate::adapter_spine::{RadioAdapter, SpineInterface};

pub struct RadioPipeline { stream: FmStream }

impl RadioPipeline {
    pub fn new() -> Self { Self { stream: FmStream::new() } }

    pub fn tick<S: SpineInterface>(
        &self, spine: &mut S, cohort_id: &str,
    ) -> Result<String, String> {
        let chunk    = self.stream.next_chunk().ok_or("stream exhausted")?;
        let features = extract_features(&chunk)?;
        drop(chunk);
        let graphlet = RadioGraphlet::from_features(features)?;
        RadioAdapter::ingest_into_spine(spine, cohort_id, graphlet)
    }
}

impl Default for RadioPipeline { fn default() -> Self { Self::new() } }

#[cfg(test)]
mod tests {
    use super::*;

    struct MockSpine { pub calls: Vec<(String, f64)> }
    impl MockSpine { fn new() -> Self { Self { calls: vec![] } } }
    impl SpineInterface for MockSpine {
        fn ingest(&mut self, cid: &str, vals: &[f64]) -> Result<String, String> {
            self.calls.push((cid.to_string(), vals[0]));
            Ok(format!("gid-{}", self.calls.len()))
        }
    }

    #[test]
    fn test_tick_produces_id() {
        let mut spine = MockSpine::new();
        let gid = RadioPipeline::new().tick(&mut spine, "c1").unwrap();
        assert!(gid.starts_with("gid-"));
        assert_eq!(spine.calls.len(), 1);
    }

    #[test]
    fn test_no_raw_signal_in_spine() {
        let mut spine = MockSpine::new();
        RadioPipeline::new().tick(&mut spine, "c1").unwrap();
        let (_, val) = &spine.calls[0];
        assert!(val.is_finite());
        assert!(*val > 0.0 && *val < 1.0);
    }

    #[test]
    fn test_adapter_rejects_nan() {
        let mut spine = MockSpine::new();
        let bad = RadioGraphlet { aggregated_value: f64::NAN, count: 1 };
        assert!(RadioAdapter::ingest_into_spine(&mut spine, "c1", bad).is_err());
    }

    #[test]
    fn test_five_ticks_consistent() {
        let mut spine = MockSpine::new();
        let p = RadioPipeline::new();
        for _ in 0..5 { p.tick(&mut spine, "c1").unwrap(); }
        assert_eq!(spine.calls.len(), 5);
        let first = spine.calls[0].1;
        for (_, v) in &spine.calls { assert!((v - first).abs() < 1e-12); }
    }
}
