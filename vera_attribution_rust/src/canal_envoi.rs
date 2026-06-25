//! canal_envoi.rs — Simule un relais d'envoi (SMTP/SMS) generique.
//!
//! Ce module ne recoit et ne voit JAMAIS le departement -- sa signature
//! de fonction ne possede structurellement aucun parametre departement.
//! Defense active : refuse aussi tout contenu qui en mentionnerait un.

#[derive(Debug)]
pub struct ErreurEnvoi(pub String);

impl std::fmt::Display for ErreurEnvoi {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}
impl std::error::Error for ErreurEnvoi {}

pub struct CanalEnvoiSimule {
    envois: Vec<(String, String)>, // (destinataire, contenu)
}

impl CanalEnvoiSimule {
    pub fn new() -> Self {
        CanalEnvoiSimule { envois: Vec::new() }
    }

    /// Signature volontairement minimaliste : (destinataire, contenu).
    /// Aucun parametre departement n'existe ici.
    pub fn envoyer(&mut self, destinataire: &str, contenu: &str) -> Result<(), ErreurEnvoi> {
        let contenu_lower = contenu.to_lowercase();
        if contenu_lower.contains("departement") || contenu_lower.contains("department") {
            return Err(ErreurEnvoi(
                "le contenu mentionne explicitement le departement -- violation du flux documente dans ATTRIBUTION_FLOW.md".to_string(),
            ));
        }
        self.envois
            .push((destinataire.to_string(), contenu.to_string()));
        Ok(())
    }

    pub fn nombre_envois(&self) -> usize {
        self.envois.len()
    }
}

impl Default for CanalEnvoiSimule {
    fn default() -> Self {
        Self::new()
    }
}