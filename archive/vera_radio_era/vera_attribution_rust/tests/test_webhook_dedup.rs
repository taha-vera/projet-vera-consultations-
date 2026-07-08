//! tests/test_webhook_dedup.rs — Verifie l'idempotence du module de
//! deduplication d'evenements webhook.

use vera_attribution::webhook_dedup::{DedupWebhook, ResultatDedup};
use std::time::Duration;

#[test]
fn test_1_premier_evenement_est_nouveau() {
    let mut dedup = DedupWebhook::new(60);
    let resultat = dedup.verifier_et_marquer("evt_abc123");
    assert_eq!(resultat, ResultatDedup::Nouveau);
    println!("OK  1. Premier evenement correctement marque comme Nouveau");
}

#[test]
fn test_2_meme_event_id_rejete_comme_duplicate() {
    let mut dedup = DedupWebhook::new(60);
    dedup.verifier_et_marquer("evt_abc123");
    let resultat = dedup.verifier_et_marquer("evt_abc123");
    assert_eq!(resultat, ResultatDedup::DejaTraite);
    println!("OK  2. Meme event_id correctement rejete comme DejaTraite (idempotence)");
}

#[test]
fn test_3_event_id_different_reste_nouveau() {
    let mut dedup = DedupWebhook::new(60);
    dedup.verifier_et_marquer("evt_abc123");
    let resultat = dedup.verifier_et_marquer("evt_xyz789");
    assert_eq!(resultat, ResultatDedup::Nouveau);
    println!("OK  3. Event_id distinct correctement traite comme Nouveau");
}

#[test]
fn test_4_purge_apres_expiration_fenetre() {
    // Fenetre tres courte pour tester la purge sans attendre 24h
    let mut dedup = DedupWebhook::new(1); // 1 seconde
    dedup.verifier_et_marquer("evt_court");
    assert_eq!(dedup.taille_actuelle(), 1);

    std::thread::sleep(Duration::from_millis(1100));

    // Un nouvel appel doit déclencher la purge et permettre de retraiter
    // le même event_id comme nouveau, puisqu'il est sorti de la fenêtre
    let resultat = dedup.verifier_et_marquer("evt_court");
    assert_eq!(
        resultat,
        ResultatDedup::Nouveau,
        "FAIL: event_id expiré encore traité comme DejaTraite"
    );
    println!("OK  4. Purge par expiration fonctionne -- pas de croissance memoire non bornee");
}

#[test]
fn test_5_taille_reste_bornee_apres_purge() {
    let mut dedup = DedupWebhook::new(1);
    for i in 0..50 {
        dedup.verifier_et_marquer(&format!("evt_{i}"));
    }
    assert_eq!(dedup.taille_actuelle(), 50);

    std::thread::sleep(Duration::from_millis(1100));
    dedup.verifier_et_marquer("evt_trigger_purge");

    assert!(
        dedup.taille_actuelle() <= 1,
        "FAIL: les anciennes entrees n'ont pas ete purgees, taille={}",
        dedup.taille_actuelle()
    );
    println!("OK  5. Taille de la structure reste bornee apres purge -- pas de fuite memoire type LRU");
}

#[test]
fn test_6_defaut_24h_raisonnable() {
    let dedup = DedupWebhook::default();
    assert_eq!(dedup.taille_actuelle(), 0);
    println!("OK  6. Fenetre par defaut (24h) instanciee sans erreur");
}
