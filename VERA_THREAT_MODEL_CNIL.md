# VERA — Modèle de Menace (Version CNIL)

## Résumé exécutif

**VERA v1** protège les données contre les attaquants externes.  
**VERA v1** ne protège pas contre un opérateur ou employé malveillant ayant accès à l'infrastructure.

---

## Deux catégories d'attaquants

### Attaquant Externe
- N'a pas d'accès à l'infrastructure
- Peut écouter le réseau, lire les disques durs s'ils sont perdus
- VERA le protège ✅

### Attaquant Interne (Opérateur / Employé)
- A accès aux serveurs, au réseau interne, au code
- Peut ajouter du logging, modifier les configurations
- VERA NE le protège pas ❌

---

## Trois scénarios réalistes

### Scénario 1 : Ingénieur CDN ajoute du logging
# Taha, je suis pas dans ton Termux — tu dois créer le fichier toi-même.
# Depuis ton Termux (dans ~/Vera-protocole-) :

cat > VERA_MODEL_A_PLUS_CCS_GRADE.md << 'EOF'
# 11. Design Model A+: CCS-Grade Ingestion Pipeline (Corrected)

[... fichier complet ci-dessus ...]
