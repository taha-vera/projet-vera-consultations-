//! rh_attribution.rs — Cote RH : genere les identifiants opaques, garde le
//! mapping email <-> id_opaque localement. Ne transmet JAMAIS l'email a VERA.
//!
//! Implemente le flux documente dans ATTRIBUTION_FLOW.md :
//!   RH connait      : email <-> id_opaque <-> departement
//!   VERA connait     : id_opaque (ephemere) <-> token <-> departement
//!   Canal d'envoi connait : email (seulement, pour adresser)
//!
//! Regle stricte : id_opaque ne doit JAMAIS porter de signification (pas de hash
//! d'email, pas de numero d'employe lisible) -- sinon il redevient un identifiant
//! indirectement nominatif.

use uuid::Uuid;
use std::collections::HashMap;
use zeroize::{Zeroize, ZeroizeOnDrop};

/// Email enveloppe pour garantir la destruction memoire via Drop.
/// Toute valeur de ce type est effacee (mise a zero) automatiquement
/// quand elle sort de portee -- contrairement a `del` en Python qui ne
/// garantit rien sur le contenu memoire reel.
#[derive(Zeroize, ZeroizeOnDrop, Clone)]
pub struct EmailSensible(String);

impl EmailSensible {
    pub fn new(email: &str) -> Self {
        EmailSensible(email.to_string())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Registre local RH : ne quitte jamais le systeme RH.
/// Le contenu (emails) est detruit en memoire de facon garantie (pas
/// seulement "oublie" comme un `del token` en Python) grace a ZeroizeOnDrop.
pub struct RegistreRH {
    correspondance: HashMap<String, EmailSensible>, // id_opaque -> email
}

impl RegistreRH {
    pub fn new() -> Self {
        RegistreRH {
            correspondance: HashMap::new(),
        }
    }

    /// Genere un id_opaque aleatoire, non signifiant, pour un participant.
    /// Retourne (id_opaque, departement) -- c'est TOUT ce qui doit partir
    /// vers VERA. L'email ne sort jamais de cette fonction vers l'exterieur.
    pub fn preparer_invitation(&mut self, email: &str, departement: &str) -> (String, String) {
        let id_opaque = Uuid::new_v4().to_string();
        self.correspondance
            .insert(id_opaque.clone(), EmailSensible::new(email));
        (id_opaque, departement.to_string())
    }

    /// Reconstitue l'email a partir de l'id_opaque -- usage RH uniquement.
    pub fn resoudre_email(&self, id_opaque: &str) -> Option<&str> {
        self.correspondance.get(id_opaque).map(|e| e.as_str())
    }

    /// Supprime l'entree apres envoi reussi -- limite la fenetre de risque.
    pub fn purger(&mut self, id_opaque: &str) {
        self.correspondance.remove(id_opaque);
    }

    pub fn taille_registre(&self) -> usize {
        self.correspondance.len()
    }
}

impl Default for RegistreRH {
    fn default() -> Self {
        Self::new()
    }
}