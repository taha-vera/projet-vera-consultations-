# ANCRE — Attestation & Noise for Confidential Radio Emissions
## A Differentially Private Aggregation Protocol for Audio Analytics

**Taha Houari**  
SAS VERA, Paris, France  
tahahouari@hotmail.fr  
github.com/taha-vera/Vera-protocole-

---

## Abstract

We present ANCRE (*Attestation & Noise for Confidential Radio Emissions*), a pure differentially private aggregation protocol for B2B audio streaming analytics. ANCRE addresses a fundamental tension in the radio industry: listening data is commercially valuable to AI operators but legally unsellable under GDPR due to privacy constraints.

ANCRE combines three technical contributions. First, a Central DP mechanism based on the trimmed mean (TMoM, α=0.1) with discrete Laplace noise (Ghosh et al., 2012), achieving pure ε=0.5-DP (δ=0) by eliminating floating-point LSB leakage (Mironov, 2012). Second, a Sybil-resistance layer via GSMA IoT SAFE SIM attestation, binding each signal to a physical SIM certificate issued by a trusted telecom operator. Third, a formal proof under substitute adjacency with explicit tie-breaking convention, yielding sensitivity Δ = 1/(0.8n) and Spearman correlation ρ = 0.9997 on the Last.fm dataset (92,834 events, 1,892 users).

The implementation (Rust v0.7, Python v0.3) passes 59+21 unit tests on Android/ARM64 (Termux), including a Kolmogorov-Smirnov test on the discrete Laplace distribution (KS stat = 0.0089 < threshold 0.020). The protocol is compliant with GDPR Articles 25 and 89, EU AI Act Article 10, and includes RFC3161 temporal anchoring (FreeTSA, March 2026). Red-team evaluation across 8 AI systems yields a consensus score of 89/100.

**Keywords**: differential privacy, audio analytics, discrete Laplace, SIM attestation, Sybil resistance, GDPR compliance, trimmed mean

---

## Résumé (Français)

Nous présentons ANCRE, un protocole de confidentialité différentielle pure pour l'analytics audio B2B. ANCRE résout la tension entre la valeur commerciale des données d'écoute radio et leur protection légale imposée par le RGPD. Le mécanisme combine une moyenne tronquée (TMoM) avec un bruit de Laplace discret exact (ε=0.5, δ=0), une couche d'attestation SIM IoT SAFE anti-Sybil, et une preuve formelle sous adjacence par substitution. L'implémentation (Rust v0.7, 59 tests) atteint ρ=0.9997 de corrélation de Spearman sur le dataset Last.fm.

