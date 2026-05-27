import hashlib
import json
import os
from datetime import datetime

CONFIG = {
    "seed": 42,
    "g1_users": 20,
    "g1_dim": 16,
    "g2_noise": 0.25,
    "bootstrap_B": 100,
    "block_size": 5,
}

def get_config_hash():
    return hashlib.md5(json.dumps(CONFIG, sort_keys=True).encode()).hexdigest()

def log_run(test_name, results):
    log_dir = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "run_log.json")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "test": test_name,
        "config_hash": get_config_hash(),
        "seed": CONFIG["seed"],
        "results": results
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    return log_entry

if __name__ == "__main__":
    print(f"Config hash: {get_config_hash()}")
    print(f"Seed: {CONFIG['seed']}")
