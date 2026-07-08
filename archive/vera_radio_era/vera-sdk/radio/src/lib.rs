//! VERA Radio SDK v0.1
//! Integration for radio operators — 3 lines to start contributing
//!
//! ```rust
//! let mut vera = VeraRadioClient::new("my-radio", 1.0);
//! vera.ingest(&fft_signal);
//! let patterns = vera.export();
//! ```

use vera_spine::collection::CollectionLayer;
use vera_spine::aggregation::AggregationLayer;
use vera_spine::dp::{privatize_value, BudgetTracker};
use vera_spine::SimpleRng;

/// Main entry point for radio operators
pub struct VeraRadioClient {
    pub station_id: String,
    rng: SimpleRng,
    collection: CollectionLayer,
    aggregation: AggregationLayer,
    budget: BudgetTracker,
    cohort_id: String,
    epsilon: f64,
}

impl VeraRadioClient {
    /// Create a new VERA client for your radio station
    /// epsilon: privacy budget (recommended: 1.0)
    pub fn new(station_id: &str, epsilon: f64) -> Self {
        let mut rng = SimpleRng::new(42);
        let mut aggregation = AggregationLayer::new(100);
        let cohort_id = aggregation.create_cohort(&mut rng);
        Self {
            station_id: station_id.to_string(),
            rng,
            collection: CollectionLayer::new(),
            aggregation,
            budget: BudgetTracker::new(epsilon * 10.0),
            cohort_id,
            epsilon,
        }
    }

    /// Ingest a signal frame (FFT magnitudes normalized 0-1)
    /// Raw data is never stored — only aggregated patterns
    pub fn ingest(&mut self, signal: &[f64]) -> Result<(), String> {
        self.budget.consume(self.epsilon / 1000.0)?;
        let cohort = self.aggregation
            .get_cohort_mut(&self.cohort_id)
            .ok_or("cohort not found")?;
        self.collection.ingest(&mut self.rng, signal.to_vec(), cohort)?;
        Ok(())
    }

    /// Export privacy-preserving patterns ready for AI operators
    pub fn export(&self) -> Vec<ExportedSignal> {
        let cohort = match self.aggregation.get_cohort(&self.cohort_id) {
            Some(c) => c,
            None => return vec![],
        };
        if !cohort.is_k_anonymous(100) {
            return vec![];
        }
        cohort.graphlets.iter().map(|g| {
            let private_value = privatize_value(
                g.aggregated_value,
                1, 1,
                g.created_at as u64,
            );
            ExportedSignal {
                station_id: self.station_id.clone(),
                aggregated_value: private_value,
                count: g.count,
                epsilon_used: self.epsilon,
                k_anonymous: true,
            }
        }).collect()
    }

    /// Budget remaining
    pub fn budget_remaining(&self) -> f64 {
        self.budget.remaining()
    }
}

/// What AI operators receive from your station
#[derive(Debug, Clone)]
pub struct ExportedSignal {
    pub station_id: String,
    pub aggregated_value: f64,
    pub count: usize,
    pub epsilon_used: f64,
    pub k_anonymous: bool,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_three_lines_integration() {
        let mut vera = VeraRadioClient::new("fip-radio", 1.0);
        let signal = vec![0.5f64; 128];
        for _ in 0..100 {
            vera.ingest(&signal).unwrap();
        }
        let patterns = vera.export();
        assert!(!patterns.is_empty());
        assert!(patterns[0].k_anonymous);
        assert_eq!(patterns[0].station_id, "fip-radio");
    }

    #[test]
    fn test_no_export_below_k100() {
        let mut vera = VeraRadioClient::new("small-radio", 1.0);
        let signal = vec![0.3f64; 128];
        for _ in 0..50 {
            vera.ingest(&signal).unwrap();
        }
        let patterns = vera.export();
        assert!(patterns.is_empty());
    }

    #[test]
    fn test_budget_decreases() {
        let mut vera = VeraRadioClient::new("test-radio", 1.0);
        let initial = vera.budget_remaining();
        vera.ingest(&[0.5f64; 128]).unwrap();
        assert!(vera.budget_remaining() < initial);
    }
}
