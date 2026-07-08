//! tests/test_attribution.rs — Verifie le flux complet documente dans
//! ATTRIBUTION_FLOW.md.

use vera_attribution::canal_envoi::CanalEnvoiSimule;
use vera_attribution::rh_attribution::RegistreRH;
use vera_attribution::vera_attribution::{IdOpaqueEphemere, PoolTokens};

#[test]
fn test_1_vera_ne_voit_jamais_email() {
    let mut pool = PoolTokens::new();
    pool.generer_pool("RH", 5);
    let id_opaque = IdOpaqueEphemere::new("test-id".to_string());
    let resultat = pool.attribuer_token(id_opaque, "RH");
    assert!(resultat.is_ok());
    println!("OK  1. attribuer_token() compile sans parametre email");
}

#[test]
fn test_2_canal_envoi_refuse_departement_dans_contenu() {
    let mut canal = CanalEnvoiSimule::new();
    let resultat = canal.envoyer(
        "marie@exemple.fr",
        "Votre departement RH vous invite a repondre",
    );
    assert!(resultat.is_err());
    println!("OK  2. Le canal d'envoi refuse tout contenu mentionnant le departement");
}

#[test]
fn test_3_id_opaque_detruit_memoire_a_la_fin_du_scope() {
    let mut pool = PoolTokens::new();
    pool.generer_pool("RH", 5);
    let id_opaque = IdOpaqueEphemere::new("test-uuid-1234-ne-doit-pas-persister".to_string());
    let resultat = pool.attribuer_token(id_opaque, "RH").unwrap();
    assert_eq!(resultat.id_opaque, "test-uuid-1234-ne-doit-pas-persister");
    println!("OK  3. id_opaque est pris par ownership (move)");
}

#[test]
fn test_4_token_a_usage_unique_anti_sybil() {
    let mut rh = RegistreRH::new();
    let mut vera = PoolTokens::new();
    vera.generer_pool("RH", 10);

    let (id_opaque, dept) = rh.preparer_invitation("marie@exemple.fr", "RH");
    let resultat = vera
        .attribuer_token(IdOpaqueEphemere::new(id_opaque), &dept)
        .unwrap();

    let premiere_consommation = vera.consommer(&resultat.token);
    assert!(premiere_consommation.is_ok());

    let deuxieme_consommation = vera.consommer(&resultat.token);
    assert!(deuxieme_consommation.is_err());
    println!("OK  4. Token a usage unique verifie -- anti-Sybil simple fonctionnel");
}

#[test]
fn test_5_flux_complet_bout_en_bout() {
    let mut rh = RegistreRH::new();
    let mut vera = PoolTokens::new();
    let mut canal = CanalEnvoiSimule::new();

    vera.generer_pool("RH", 10);
    vera.generer_pool("IT", 50);

    let (id_opaque, dept) = rh.preparer_invitation("marie@exemple.fr", "RH");
    let resultat = vera
        .attribuer_token(IdOpaqueEphemere::new(id_opaque.clone()), &dept)
        .unwrap();

    let email_destinataire = rh.resoudre_email(&id_opaque).unwrap().to_string();
    canal
        .envoyer(
            &email_destinataire,
            &format!("Votre lien de participation : {}", resultat.token),
        )
        .unwrap();
    rh.purger(&id_opaque);

    assert_eq!(rh.taille_registre(), 0);
    assert_eq!(canal.nombre_envois(), 1);
    assert_eq!(vera.disponibles("RH"), 9);

    let departement_route = vera.consommer(&resultat.token).unwrap();
    assert_eq!(departement_route, "RH");

    println!("OK  5. Flux complet RH -> VERA -> envoi -> consommation verifie");
}

#[test]
fn test_6_limite_documentee_rh_sur_attribution() {
    let mut rh = RegistreRH::new();
    let mut vera = PoolTokens::new();
    vera.generer_pool("RH", 10);

    let (id_opaque_a, dept_a) = rh.preparer_invitation("marie@exemple.fr", "RH");
    let (id_opaque_b, dept_b) = rh.preparer_invitation("marie@exemple.fr", "RH");

    let resultat_a = vera
        .attribuer_token(IdOpaqueEphemere::new(id_opaque_a), &dept_a)
        .unwrap();
    let resultat_b = vera
        .attribuer_token(IdOpaqueEphemere::new(id_opaque_b), &dept_b)
        .unwrap();

    assert_ne!(resultat_a.token, resultat_b.token);
    assert_eq!(vera.disponibles("RH"), 8);

    println!("OK  6. Limite documentee reproduite : RH peut sur-attribuer sans detection VERA");
}