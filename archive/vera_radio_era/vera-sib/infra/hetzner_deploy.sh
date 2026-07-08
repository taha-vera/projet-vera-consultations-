#!/bin/bash
# VERA Hetzner Deployment (30 minutes)
set -e

echo "VERA Production Deployment on Hetzner"

# 1. System
apt-get update && apt-get install -y python3-pip postgresql nginx git curl certbot

# 2. VERA repo
git clone https://github.com/taha-vera/Protocole-Vera.git /opt/vera
cd /opt/vera

# 3. Python deps
pip3 install flask psycopg2-binary python-dotenv numpy

# 4. PostgreSQL init
sudo -u postgres createdb vera_phase2
sudo -u postgres psql vera_phase2 << SQL
CREATE TABLE tracks (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255),
  artist VARCHAR(255),
  duration INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE immutable_audit (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(50),
  timestamp TIMESTAMP DEFAULT NOW(),
  data_hash VARCHAR(256)
);
SQL

# 5. Systemd service
cat > /etc/systemd/system/vera-api.service << SYSTEMD
[Unit]
Description=VERA API
After=network.target postgresql.service

[Service]
User=vera
WorkingDirectory=/opt/vera
ExecStart=/usr/bin/python3 /opt/vera/vera-sib/api/vera_api.py
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload && systemctl enable vera-api && systemctl start vera-api

echo "✅ VERA ready at http://localhost:5000/api/v1/health"
