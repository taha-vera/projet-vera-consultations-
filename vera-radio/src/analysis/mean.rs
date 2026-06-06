pub fn detect_mean(signal: &[u8]) -> f64 {
    if signal.is_empty() { return 0.3; }
    let samples: Vec<f32> = signal.chunks(4)
        .filter_map(|c| if c.len() == 4 {
            let v = f32::from_le_bytes([c[0],c[1],c[2],c[3]]);
            if v.is_finite() { Some(v) } else { None }
        } else { None })
        .collect();
    if samples.is_empty() { return 0.3; }
    let mean = samples.iter().sum::<f32>() / samples.len() as f32;
    ((mean.abs() * 10.0).tanh() as f64).clamp(0.0, 1.0)
}
