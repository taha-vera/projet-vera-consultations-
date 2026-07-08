#!/bin/bash
# VERA Phase 2 W3 Deployment
set -e

echo "VERA Production Deployment"

apt-get update && apt-get install -y python3-pip postgresql nginx git
cd /opt
git clone https://github.com/taha-vera/Protocole-Vera.git vera || true
cd vera
pip3 install flask psycopg2-binary numpy

echo "PostgreSQL setup..."
sudo -u postgres psql << SQL
CREATE DATABASE vera_phase2;
CREATE USER vera_user WITH PASSWORD 'vera2026';
GRANT ALL ON DATABASE vera_phase2 TO vera_user;
SQL

echo "Systemd service..."
cat > /etc/systemd/system/vera-api.service << SYSTEMD
[Unit]
Description=VERA API
After=network.target

[Service]
User=vera
WorkingDirectory=/opt/vera
ExecStart=/usr/bin/python3 /opt/vera/vera-sib/api/vera_api.py
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD

useradd -m vera || true
chown -R vera:vera /opt/vera

systemctl daemon-reload
systemctl enable vera-api
systemctl start vera-api

echo "✅ VERA live at http://localhost:5000/api/v1/health"
