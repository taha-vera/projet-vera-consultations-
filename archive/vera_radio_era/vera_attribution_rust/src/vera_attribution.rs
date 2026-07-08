//! vera_attribution.rs — Cote VERA : pool de tokens par cohorte, attribution
//! via id_opaque. VERA ne recoit JAMAIS l'email.
//!
//! Garde-fous obligatoires (cf. ATTRIBUTION_FLOW.md, "Regle operationnelle") :
//!   - id_opaque est pris par VALEUR (ownership), jamais par reference --
//!     ce qui force le compilateur a garantir qu'aucune copie ne survit
//!     silencieusement ailleurs dans le programme.
//!   - id_opaque implemente Zeroize : sa memoire est explicitement
//!     reecrite a la fin de son scope, contrairement a `del` en Python
//!     qui ne fait que retirer une reference.
//!   - aucune structure de PoolTokens ne stocke jamais id_opaque.

use rand::RngCore;
use std::collections::{HashMap, HashSet};
use zeroize::{Zeroize, ZeroizeOnDrop};

#[derive(Debug)]
pub enum ErreurAttribution {
    PoolEpuiseOuInexistant(String),
    TokenDejaConsomme,
    TokenInconnu,
}

impl std::fmt::Display for ErreurAttribution {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::PoolEpuiseOuInexistant(d) => {
                write!(f, "pool epuise ou inexistant pour departement={d}")
            }
            Self::TokenDejaConsomme => write!(f, "token deja consomme -- une reponse par token"),
            Self::TokenInconnu => write!(f, "token inconnu ou jamais attribue"),
        }
    }
}

impl std::error::Error for ErreurAttribution {}

/// Resultat d'attribution. id_opaque est inclus pour la correlation de la
/// reponse HTTP cote RH -- mais ce struct lui-meme n'est jamais conserve
/// par VERA apres avoir ete renvoye a l'appelant (cf. attribuer_token).
pub struct ResultatAttribution {
    pub id_opaque: String,
    pub token: String,
}

pub struct PoolTokens {
    pools: HashMap<String, HashSet<String>>, // departement -> set(token)
    registre_attribution: HashMap<String, String>, // token -> departement (PAS d'identite)
    tokens_consommes: HashSet<String>,
}

impl PoolTokens {
    pub fn new() -> Self {
        PoolTokens {
            pools: HashMap::new(),
            registre_attribution: HashMap::new(),
            tokens_consommes: HashSet::new(),
        }
    }

    fn generer_token() -> String {
        let mut bytes = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut bytes);
        use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
        URL_SAFE_NO_PAD.encode(bytes)
    }

    /// RH transmet seulement un quota par departement -- jamais de liste nominative.
    pub fn generer_pool(&mut self, departement: &str, quantite: usize) {
        let pool = self.pools.entry(departement.to_string()).or_default();
        for _ in 0..quantite {
            let token = Self::generer_token();
            pool.insert(token.clone());
            self.registre_attribution
                .insert(token, departement.to_string());
        }
    }

    pub fn disponibles(&self, departement: &str) -> usize {
        self.pools.get(departement).map(|p| p.len()).unwrap_or(0)
    }

    pub fn attribuer_token(
        &mut self,
        id_opaque: IdOpaqueEphemere,
        departement: &str,
    ) -> Result<ResultatAttribution, ErreurAttribution> {
        let pool = self
            .pools
            .get_mut(departement)
            .filter(|p| !p.is_empty())
            .ok_or_else(|| ErreurAttribution::PoolEpuiseOuInexistant(departement.to_string()))?;

        let token = pool.iter().next().cloned().unwrap();
        pool.remove(&token);

        let id_opaque_str = id_opaque.into_inner();
        Ok(ResultatAttribution {
            id_opaque: id_opaque_str,
            token,
        })
    }

    pub fn consommer(&mut self, token: &str) -> Result<String, ErreurAttribution> {
        if self.tokens_consommes.contains(token) {
            return Err(ErreurAttribution::TokenDejaConsomme);
        }
        let departement = self
            .registre_attribution
            .get(token)
            .ok_or(ErreurAttribution::TokenInconnu)?
            .clone();
        self.tokens_consommes.insert(token.to_string());
        Ok(departement)
    }
}

impl Default for PoolTokens {
    fn default() -> Self {
        Self::new()
    }
}

/// Wrapper pour id_opaque garantissant l'effacement memoire a la fin de
/// son scope (Drop). A passer PAR VALEUR aux fonctions qui le consomment.
#[derive(Zeroize, ZeroizeOnDrop)]
pub struct IdOpaqueEphemere(String);

impl IdOpaqueEphemere {
    pub fn new(valeur: String) -> Self {
        IdOpaqueEphemere(valeur)
    }

    pub fn into_inner(mut self) -> String {
        std::mem::take(&mut self.0)
    }
}