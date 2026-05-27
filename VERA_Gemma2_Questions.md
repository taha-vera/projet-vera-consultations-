# VERA Protocol – Gemma 2 2B Integration

## Technical Questions for Route Local Implementation

Date: May 26, 2026

### 1. Gemma 2 2B Quantization

1.1 Quantization: q4_K_M vs q4_0 vs q4_K_S?
1.2 Final .gguf size estimate?
1.3 p50/p95 latency on Snapdragon 8 Gen 3, MediaTek, Cortex-X4?

### 2. NPU Integration

2.1 Qualcomm AI Engine Direct vs MediaTek Neuron vs LiteRT?
2.2 Precision loss NPU int8 vs CPU fp16?
2.3 Fallback: runtime detection or build-time variants?

### 3. Sensitivity Classification

3.1 Rule-based or 200M model for v1?
3.2 Latency < 50ms realistic?

### 4. VERA Core v2 Integration

4.1 Gemma in same TEE or separate process?
4.2 mmap model weights or copy .gguf?

### 5. Baseline: < 900ms, > 80% Success

5.1 French dataset recommended?
5.2 Exact match or human eval?

### 6. Timeline & Resources

Expected: Technical recs, risk assessment, FTE estimate, go/no-go

---

VERA Core v2: Rust (1150 LOC), TEE attestation, Anti-replay ledger, Epsilon (e=1.5)
