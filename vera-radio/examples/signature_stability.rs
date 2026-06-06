use std::thread::sleep;
use std::time::Duration;
use vera_radio::capture::fm::FmStream;
use vera_radio::analysis::extract_features;

fn mean_std(xs: &[f64]) -> (f64, f64) {
    if xs.is_empty() { return (0.0, 0.0); }
    let n = xs.len() as f64;
    let m = xs.iter().sum::<f64>() / n;
    let v = xs.iter().map(|x| (x - m).powi(2)).sum::<f64>() / n;
    (m, v.sqrt())
}

fn main() {
    let stations: Vec<(&str, &str)> = vec![
        ("fip",            "http://icecast.radiofrance.fr/fip-hifi.aac"),
        ("france-inter",   "http://icecast.radiofrance.fr/franceinter-hifi.aac"),
        ("france-culture", "http://icecast.radiofrance.fr/franceculture-hifi.aac"),
        ("france-musique", "http://icecast.radiofrance.fr/francemusique-hifi.aac"),
        ("france-info",    "http://icecast.radiofrance.fr/franceinfo-hifi.aac"),
        ("mouv",           "http://icecast.radiofrance.fr/mouv-hifi.aac"),
    ];
    let n_windows = 20;
    let pause = Duration::from_secs(20);

    for (name, url) in &stations {
        let stream = FmStream::with_url(url);
        let mut energies = Vec::new();
        let mut zcrs = Vec::new();
        for i in 0..n_windows {
            if let Some(pcm) = stream.next_chunk() {
                if let Ok(f) = extract_features(&pcm) {
                    energies.push(f.energy);
                    zcrs.push(f.zcr);
                }
            }
            if i + 1 < n_windows { sleep(pause); }
        }
        let (e_m, e_s) = mean_std(&energies);
        let (z_m, z_s) = mean_std(&zcrs);
        println!(
            "{:<14} energy {:.4} +/- {:.4}   zcr {:.4} +/- {:.4}   (n={})",
            name, e_m, e_s, z_m, z_s, energies.len()
        );
    }
}
