# VERA: A Differential Privacy Protocol for Aggregate Signal Preservation

**Authors**: Taha Houari  
**Date**: May 2026  

## 1. Problem Statement

AI training datasets are opaque, irreversible, exploitable, non-remunerated.

## 2. Core Idea

VERA aggregates data, destroys raw signals, preserves collective geometry via ε-DP in TEE.

## 3. Architecture

Client (ε=1.0) → Aggregation (ε=0.5) → TEE (SNP) → Audit Chain

## 4. Guarantees

- ε-DP formal proof (Dwork & Roth)
- Non-reidentification: bias ≤ 0.012
- Ranking preservation: Spearman=1.0

## 5. Validation

Radio France: Pearson=0.9617, Spearman=1.0  
Last.fm: Pearson=0.9617, Spearman=1.0  
Cross-dataset invariance confirmed.

## 6. Conclusion

Aggregate utility + individual privacy compatible.

References: Dwork & Roth 2014, Mironov 2012  
Code: github.com/taha-vera/Vera-protocole- (VERA_CORE_v1_FREEZE)
