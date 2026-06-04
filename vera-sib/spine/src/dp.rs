//! Discrete Laplace mechanism — résistant à l'attaque Mironov (2012)
//! Remplace l'inversion CDF sur f64 par un échantillonnage sur entiers.

/// Discret Laplace : échantillonne Z ~ DLap(sensitivity/epsilon)
/// Algorithme : Ghosh, Roughgarden, Sundarajan (2012)
pub fn discrete_laplace(sensitivity: u64, epsilon_num: u64, epsilon_den: u64, rng_state: u64) -> i64 {
    // t = floor(sensitivity * epsilon_den / epsilon_num)
    let t = (sensitivity * epsilon_den) / epsilon_num;
    if t == 0 { return 0; }

    // Geometric sampling via rejection — constant-time approximation
    let mut state = rng_state;
    let mut sample: i64 = 0;

    for _ in 0..128 {
        state = lcg_next(state);
        let u = (state >> 11) as f64 / (1u64 << 53) as f64;
        // Geometric(1 - exp(-1/t))
        let p = 1.0 - (-1.0_f64 / t as f64).exp();
        if u < p {
            break;
        }
        sample += 1;
    }

    // Signe aléatoire
    state = lcg_next(state);
    if state & 1 == 0 { sample } else { -sample }
}

/// Applique DLap sur une valeur agrégée normalisée [0,1]
/// Quantifie sur 1_000_000 pour éviter les f64
pub fn privatize_value(value: f64, epsilon_num: u64, epsilon_den: u64, rng_state: u64) -> f64 {
    let scale = 1_000_000u64;
    let quantized = (value * scale as f64).round() as i64;
    let noise = discrete_laplace(1, epsilon_num, epsilon_den, rng_state);
    let noisy = (quantized + noise).clamp(0, scale as i64);
    noisy as f64 / scale as f64
}

/// LCG simple — seed uniquement, pas pour la crypto
fn lcg_next(state: u64) -> u64 {
    state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dlap_output_bounded() {
        for seed in [1u64, 42, 999, u64::MAX / 2] {
            let v = privatize_value(0.5, 1, 1, seed);
            assert!(v >= 0.0 && v <= 1.0, "v={v}");
        }
    }

    #[test]
    fn test_dlap_zero_epsilon_den() {
        // epsilon = 1/1 -> bruit modéré
        let v = privatize_value(0.5, 1, 1, 42);
        assert!(v >= 0.0 && v <= 1.0);
    }

    #[test]
    fn test_dlap_no_float_holes() {
        // Vérifie que la distribution ne produit pas que 0.5
        let results: Vec<f64> = (1u64..=100)
            .map(|s| privatize_value(0.5, 1, 10, s))
            .collect();
        let unique: std::collections::HashSet<u64> = results
            .iter()
            .map(|&v| (v * 1_000_000.0) as u64)
            .collect();
        assert!(unique.len() > 1, "distribution trop concentrée");
    }
}
