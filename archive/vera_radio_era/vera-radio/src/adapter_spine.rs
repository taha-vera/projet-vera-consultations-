use crate::graphlet_builder::RadioGraphlet;

pub trait SpineInterface {
    fn ingest(&mut self, cohort_id: &str, values: &[f64]) -> Result<String, String>;
}

pub struct RadioAdapter;

impl RadioAdapter {
    pub fn ingest_into_spine<S: SpineInterface>(
        spine:     &mut S,
        cohort_id: &str,
        graphlet:  RadioGraphlet,
    ) -> Result<String, String> {
        if !graphlet.aggregated_value.is_finite() {
            return Err(format!("non-finite aggregated_value: {}", graphlet.aggregated_value));
        }
        spine.ingest(cohort_id, &[graphlet.aggregated_value])
    }
}
