#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# EC2 Cloud-Init Bootstrap Script (Runs automatically on first boot as root)
# ==============================================================================

set -euo pipefail
exec > >(tee -a /var/log/onion_bootstrap.log) 2>&1

echo "=================================================================="
echo "  🧅 Starting Onion Grading EC2 Cloud-Init Bootstrap"
echo "  Timestamp: $(date -u)"
echo "=================================================================="

# 1. Configure 2GB Swap Space
if [[ ! -f /swapfile ]]; then
  echo "[1/7] Creating 2GB Swapfile..."
  fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl vm.swappiness=10
  echo 'vm.swappiness=10' >> /etc/sysctl.conf
  echo "✓ Swap configured."
fi

# 2. Install System Dependencies
echo "[2/7] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  python3-venv \
  git \
  curl \
  wget \
  libgl1 \
  libglib2.0-0 \
  build-essential

# 3. Install Astral UV (Fast Python Manager)
echo "[3/7] Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh
chmod +x /usr/local/bin/uv || true

# 4. Install Cloudflare Tunnel CLI (cloudflared)
echo "[4/7] Installing cloudflared..."
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
  CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
else
  CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
fi
wget -q -O /usr/local/bin/cloudflared "$CF_URL"
chmod +x /usr/local/bin/cloudflared

# 5. Clone Repository on deploy branch
APP_DIR="/home/ubuntu/Onion-Grading"
echo "[5/7] Cloning Onion-Grading repository (branch: deploy)..."
rm -rf "$APP_DIR"
git clone --depth 1 -b deploy https://github.com/Tanishquppal220/Onion-Grading.git "$APP_DIR"
chown -R ubuntu:ubuntu "$APP_DIR"

# 6. Setup Python 3.12 Virtualenv with PyTorch CPU
echo "[6/7] Setting up Python virtual environment with PyTorch CPU..."
cd "$APP_DIR/backend"
sudo -u ubuntu /usr/local/bin/uv sync

# 7. Configure and Start Systemd Services
echo "[7/7] Configuring systemd services..."

# Ensure cloudflared log file exists with write permissions for ubuntu user
touch /var/log/cloudflared.log
chmod 666 /var/log/cloudflared.log

# Service 1: Backend FastAPI
cat << 'EOF' > /etc/systemd/system/onion-grading.service
[Unit]
Description=Onion Quality Assessment & Autonomous Grading Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Onion-Grading/backend
ExecStart=/home/ubuntu/Onion-Grading/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Service 2: Cloudflare Quick Tunnel
cat << 'EOF' > /etc/systemd/system/onion-tunnel.service
[Unit]
Description=Cloudflare Quick Tunnel for Onion Grading
After=onion-grading.service
Wants=onion-grading.service

[Service]
Type=simple
User=ubuntu
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:8000 --logfile /var/log/cloudflared.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable onion-grading.service onion-tunnel.service
systemctl restart onion-grading.service onion-tunnel.service

# Wait for tunnel URL to generate and record it
echo "Extracting Cloudflare HTTPS tunnel URL..."
TUNNEL_URL=""
for i in {1..30}; do
  if [[ -f /var/log/cloudflared.log ]]; then
    TUNNEL_URL=$(grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /var/log/cloudflared.log | tail -n 1 || true)
    if [[ -n "$TUNNEL_URL" ]]; then
      break
    fi
  fi
  sleep 2
done

if [[ -n "$TUNNEL_URL" ]]; then
  echo "$TUNNEL_URL" > /home/ubuntu/TUNNEL_URL.txt
  echo "$TUNNEL_URL" > /var/log/tunnel_url.txt
  chown ubuntu:ubuntu /home/ubuntu/TUNNEL_URL.txt
  echo "✓ Tunnel URL generated: $TUNNEL_URL"
else
  echo "Warning: Tunnel URL not captured in time. Check /var/log/cloudflared.log"
fi

# Signal completion
touch /home/ubuntu/BOOTSTRAP_COMPLETE
chown ubuntu:ubuntu /home/ubuntu/BOOTSTRAP_COMPLETE
echo "=================================================================="
echo "  🎉 Bootstrap completed successfully at $(date -u)"
echo "=================================================================="
