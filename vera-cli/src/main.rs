use std::env;
use std::process::Command;

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 2 {
        print_help();
        return;
    }

    match args[1].as_str() {
        "setup"  => cmd_setup(),
        "test"   => cmd_test(),
        "deploy" => cmd_deploy(),
        "audit"  => cmd_audit(),
        "import" => cmd_import(),
        _        => {
            eprintln!("Commande inconnue: {}", args[1]);
            print_help();
        }
    }
}

fn print_help() {
    println!("VERA CLI v0.1.0");
    println!("Usage: vera <commande>");
    println!("");
    println!("Commandes:");
    println!("  setup   — Initialise l'environnement VERA");
    println!("  test    — Lance tous les tests (Rust + Python)");
    println!("  deploy  — Déploie sur le serveur");
    println!("  audit   — Vérifie les invariants SPINE");
    println!("  import  — Importe un nouveau flux de données");
}

fn cmd_setup() {
    println!("[VERA] Setup...");
    run("cargo", &["build", "--workspace"]);
    println!("[VERA] Setup OK");
}

fn cmd_test() {
    println!("[VERA] Tests Rust...");
    run("cargo", &["test", "--workspace", "--lib"]);
    println!("[VERA] Tests Python SIB...");
    std::env::set_current_dir("vera-sib").unwrap();
    run("python", &["run_all_tests.py"]);
    std::env::set_current_dir("..").unwrap();
    println!("[VERA] Tous les tests OK");
}

fn cmd_deploy() {
    println!("[VERA] Deploy...");
    run("bash", &["vera-sib/w3/deploy.sh"]);
}

fn cmd_audit() {
    println!("[VERA] Audit invariants SPINE...");
    run("cargo", &["test", "--workspace", "--lib", "--", "invariant"]);
    println!("[VERA] Audit OK");
}

fn cmd_import() {
    println!("[VERA] Import flux...");
    run("cargo", &["run", "-p", "vera-radio"]);
}

fn run(cmd: &str, args: &[&str]) {
    let status = Command::new(cmd)
        .args(args)
        .status()
        .expect(&format!("Erreur: impossible de lancer {}", cmd));
    if !status.success() {
        eprintln!("[VERA] Echec: {} {:?}", cmd, args);
        std::process::exit(1);
    }
}
