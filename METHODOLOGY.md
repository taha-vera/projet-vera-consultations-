# VERA - Methodology

## Pipeline

Radio France AAC stream
-> ureq HTTP capture
-> symphonia AAC decoder -> PCM float32
-> feature extraction (energy, variance, mean)
-> zeroize PCM samples (Invariant I)
-> vera-spine DP aggregation
-> orphaned statistics exported

## Why Symphonia

Symphonia was chosen over FFmpeg for three reasons:
1. Pure Rust - no C FFI, no unsafe memory
2. AAC support - native decode of Radio France streams
3. Compatible with VERA zeroize invariant

Without symphonia: features measure codec properties (std ~0.004)
With symphonia: features measure audio content (std ~0.06)
15x better discrimination.

## Features

energy   = sqrt(mean(x^2)).tanh()  - RMS amplitude
variance = sqrt(var(x)).tanh()     - Signal dynamics
mean     = (mean(abs(x))*10).tanh() - Spectral balance

## Why Zeroize

PCM samples destroyed immediately after feature extraction.
Enforces Invariant I (Non-persistence).
Prevents cold-boot and memory-scraping attacks.

## Parameters

Chunk size : 128KB AAC (~3s at 320kbps)
Packets    : 4 per chunk
k-anonymity: >= 100 (Invariant II)
epsilon    : 1.0 default
Half-life  : 24h (Invariant III)

## Limitations

1. Single chunk (~3s) - not a long-term average
2. energy and variance correlated - future: ZCR, spectral centroid
3. No ground truth labels - discrimination is relative

## Reproducibility

git clone https://github.com/taha-vera/Protocole-Vera
cd Protocole-Vera
cargo test -p vera-radio multiradio --lib -- --nocapture

Requires: Rust 1.70+, internet access to Radio France streams.
