pub fn detect_variance(signal: &[u8]) -> f64 {
    if signal.is_empty() { return 0.3; }
    let samples: Vec<f32> = signal.chunks(4)
        .filter_map(|c| if c.len() == 4 {
            let v = f32::from_le_bytes([c[0],c[1],c[2],c[3]]);
            if v.is_finite() { Some(v) } else { None }
        } else { None })
        .collect();
    if samples.is_empty() { return 0.3; }
    let mean = samples.iter().sum::<f32>() / samples.len() as f32;
    let variance = samples.iter().map(|s| (s-mean).powi(2)).sum::<f32>() / samples.len() as f32;
    (variance.sqrt().tanh() as f64).clamp(0.0, 1.0)
}
