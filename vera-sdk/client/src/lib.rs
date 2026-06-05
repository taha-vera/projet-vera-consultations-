//! VERA Client SDK v0.1
//! For AI operators — purchase legal cultural data
//!
//! ```rust
//! let client = VeraClientSDK::new("mistral", 100.0);
//! let patterns = client.purchase(signals);
//! let receipt = client.get_receipt();
//! ```


/// Purchased pattern from VERA network
#[derive(Debug, Clone)]
pub struct PurchasedPattern {
    pub pattern_id: String,
    pub station_id: String,
    pub aggregated_value: f64,
    pub count: usize,
    pub epsilon_guaranteed: f64,
    pub k_anonymous: bool,
    pub price: f64,
}

/// Purchase receipt for audit trail
#[derive(Debug, Clone)]
pub struct PurchaseReceipt {
    pub operator_id: String,
    pub total_patterns: usize,
    pub total_price: f64,
    pub redistribution_amount: f64,
    pub vera_commission: f64,
}

/// VERA client for AI operators
pub struct VeraClientSDK {
    pub operator_id: String,
    pub budget: f64,
    pub spent: f64,
    receipts: Vec<PurchaseReceipt>,
}

impl VeraClientSDK {
    /// Create a new VERA client
    /// budget: maximum spend in euros
    pub fn new(operator_id: &str, budget: f64) -> Self {
        Self {
            operator_id: operator_id.to_string(),
            budget,
            spent: 0.0,
            receipts: Vec::new(),
        }
    }

    /// Purchase patterns from VERA network
    /// Automatically calculates redistribution
    pub fn purchase(&mut self, patterns: Vec<PurchasedPattern>) -> Result<PurchaseReceipt, String> {
        let total_price: f64 = patterns.iter().map(|p| p.price).sum();

        if self.spent + total_price > self.budget {
            return Err(format!(
                "Budget exceeded: spent={:.2} + cost={:.2} > budget={:.2}",
                self.spent, total_price, self.budget
            ));
        }

        // VERA is a proof protocol.
        // It does not redistribute revenue.
        // Redistribution is handled by collective management organizations.
        let redistribution = 0.0; // VERA does not redistribute
        // SACEM decides internal split
        

        let receipt = PurchaseReceipt {
            operator_id: self.operator_id.clone(),
            total_patterns: patterns.len(),
            total_price,
            redistribution_amount: redistribution,
            vera_commission: 0.0, // VERA does not take commission
        };

        self.spent += total_price;
        self.receipts.push(receipt.clone());
        Ok(receipt)
    }

    pub fn budget_remaining(&self) -> f64 {
        self.budget - self.spent
    }

    pub fn get_receipts(&self) -> &Vec<PurchaseReceipt> {
        &self.receipts
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mock_patterns(n: usize, price: f64) -> Vec<PurchasedPattern> {
        (0..n).map(|i| PurchasedPattern {
            pattern_id: format!("p{}", i),
            station_id: "fip-radio".to_string(),
            aggregated_value: 0.5,
            count: 150,
            epsilon_guaranteed: 1.0,
            k_anonymous: true,
            price,
        }).collect()
    }

    #[test]
    fn test_purchase_ok() {
        let mut client = VeraClientSDK::new("mistral", 1000.0);
        let patterns = mock_patterns(10, 10.0);
        let receipt = client.purchase(patterns).unwrap();
        assert_eq!(receipt.total_patterns, 10);
        assert!((receipt.total_price - 100.0).abs() < 1e-9);
        assert_eq!(receipt.vera_commission, 0.0);
        assert_eq!(receipt.redistribution_amount, 0.0);
    }

    #[test]
    fn test_budget_exceeded() {
        let mut client = VeraClientSDK::new("small-operator", 50.0);
        let patterns = mock_patterns(10, 10.0);
        assert!(client.purchase(patterns).is_err());
    }

    #[test]
    fn test_redistribution_model() {
        let mut client = VeraClientSDK::new("openai", 10000.0);
        let patterns = mock_patterns(1, 100.0);
        let receipt = client.purchase(patterns).unwrap();
        // 60% contributors + 25% rights = 85% redistributed
        assert_eq!(receipt.redistribution_amount, 0.0);
        // 15% VERA commission
        assert_eq!(receipt.vera_commission, 0.0);
    }
}
