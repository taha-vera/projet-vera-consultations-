# VERA Complete Specification v1.0

**Purpose**: Detailed threat model & attack surface analysis  
**Status**: Basis for CCS-grade review  

---

## 1. Client-Side Pipeline

### 1.1 Input
- Raw listening event: (user_id, artist_id, timestamp, duration)
- Per-device clipping: max 1 listen per station per day

### 1.2 Randomized Response (ε_client = 1.0)
```python
def randomized_response(artist_id, epsilon=1.0):
    p_truth = 1 / (1 + exp(epsilon))  # ~0.27 at ε=1.0
    if random() < p_truth:
        return artist_id  # Truth
    else:
        return random_artist()  # Lie
# Crée la spec complète
cat > VERA_COMPLETE_SPECIFICATION.md << 'EOF'
# VERA Complete Specification v1.0

[contenu complet du document ci-dessus]

