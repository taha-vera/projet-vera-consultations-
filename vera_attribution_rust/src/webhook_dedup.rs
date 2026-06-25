//! webhook_dedup.rs — Deduplication des evenements webhook entrants (Formbricks
//! ou tout systeme equivalent), pour garantir l'idempotence du traitement VERA
//! face aux livraisons dupliquees (retry reseau, replay involontaire).
//!
//! Principe distinct d'INFRA-4 (nonce client + fenetre 60s pour reveal()) :
//! ici la source de verite pour la deduplication est l'event_id stable fourni
//! par l'emetteur (Formbricks garantit un ID stable pour tous les essais de
//! livraison d'un meme evenement, y compris les retries), pas un nonce genere
//! par VERA. On reutilise le principe (fenetre temporelle + cle vue/non-vue)
//! mais pas le mecanisme exact, car le contexte differe : ici VERA est
//! consommateur passif d'un flux qu'il ne controle pas.

use std::collections::HashMap;
use std::time::{Duration, Instant};

#[derive(Debug, PartialEq)]
pub enum ResultatDedup {
    Nouveau,
    DejaTraite,
}

pub struct DedupWebhook {
    /// event_id -> instant de premiere reception
    vus: HashMap<String, Instant>,
    fenetre: Duration,
}

impl DedupWebhook {
    /// fenetre_secondes : duree de conservation d'un event_id avant purge.
    /// Doit couvrir la fenetre de retry realiste de l'emetteur (Formbricks
    /// documente des retries avec backoff ; une fenetre de 24h est large
    /// mais sans cout memoire significatif a l'echelle d'une campagne).
    pub fn new(fenetre_secondes: u64) -> Self {
        DedupWebhook {
            vus: HashMap::new(),
            fenetre: Duration::from_secs(fenetre_secondes),
        }
    }

    /// Verifie si cet event_id a deja ete traite. Si non, l'enregistre et
    /// retourne Nouveau -- l'appelant doit alors proceder au traitement.
    /// Si deja vu (dans la fenetre), retourne DejaTraite -- l'appelant doit
    /// ignorer silencieusement (repondre 200 OK sans recalculer, comme
    /// recommande pour les webhooks idempotents).
    pub fn verifier_et_marquer(&mut self, event_id: &str) -> ResultatDedup {
        self.purger_expires();

        if self.vus.contains_key(event_id) {
            return ResultatDedup::DejaTraite;
        }

        self.vus.insert(event_id.to_string(), Instant::now());
        ResultatDedup::Nouveau
    }

    /// Purge les entrees hors fenetre -- empeche une croissance memoire non
    /// bornee sur une instance VERA longue duree (cf. lecon retenue du bug
    /// LRU/memoire deja rencontre sur le module NAV : ne jamais laisser une
    /// structure de dedup croitre sans purge explicite).
    fn purger_expires(&mut self) {
        let maintenant = Instant::now();
        self.vus
            .retain(|_, &mut instant| maintenant.duration_since(instant) < self.fenetre);
    }

    pub fn taille_actuelle(&self) -> usize {
        self.vus.len()
    }
}

impl Default for DedupWebhook {
    fn default() -> Self {
        // 24h par defaut : couvre largement les fenetres de retry observees
        // chez les emetteurs de webhooks standards (Formbricks, Stripe, etc.)
        Self::new(86400)
    }
}
