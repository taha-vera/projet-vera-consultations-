pub fn detect_zcr(signal: &[u8]) -> f64 {
    if signal.len() < 8 { return 0.0; }
    let samples: Vec<f32> = signal.chunks(4)
        .filter_map(|c| if c.len() == 4 {
            let v = f32::from_le_bytes([c[0],c[1],c[2],c[3]]);
            if v.is_finite() { Some(v) } else { None }
        } else { None })
        .collect();
    if samples.len() < 2 { return 0.0; }
    let crossings = samples.windows(2)
        .filter(|w| (w[0] >= 0.0) != (w[1] >= 0.0))
        .count();
    let zcr = crossings as f64 / samples.len() as f64;
    zcr.clamp(0.0, 1.0)
}
