use hdrhistogram::Histogram;
use parking_lot::RwLock;
use std::sync::Arc;

pub struct LatencyMetrics {
    histogram: Arc<RwLock<Histogram<u64>>>,
}

impl LatencyMetrics {
    pub fn new() -> Self {
        let histogram = Histogram::new(3).unwrap();
        Self {
            histogram: Arc::new(RwLock::new(histogram)),
        }
    }

    pub fn record_latency(&self, latency_ms: u32) {
        let _ = self.histogram.write().record(latency_ms as u64 * 1000);
    }

    pub fn p50(&self) -> Option<u32> {
        let hist = self.histogram.read();
        if hist.count() == 0 { None } else { Some((hist.value_at_percentile(50.0) / 1000) as u32) }
    }

    pub fn p95(&self) -> Option<u32> {
        let hist = self.histogram.read();
        if hist.count() == 0 { None } else { Some((hist.value_at_percentile(95.0) / 1000) as u32) }
    }
}
