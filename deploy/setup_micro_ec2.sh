#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# EC2 Micro Instance Setup Script (Ubuntu 24.04 LTS)
#
# Configures 2GB swap, installs system packages, uv, cloudflared,
# and starts the production systemd service.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=================================================================="
echo "  🧅 Bootstrapping Onion Grading on EC2 Micro Instance"
echo "  Project root: $PROJECT_ROOT"
echo "=================================================================="

# 1. Configure 2GB Swap (Crucial for 1GB RAM instances to avoid OOM)
if [[ ! -f /swapfile ]]; then
  echo -e "\n[1/6] Allocating 2GB Swapfile..."
  sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  if ! grep -q '/swapfile' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  fi
  sudo sysctl vm.swappiness=10
  echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
  echo "✓ 2GB Swap activated successfully."
else
  echo -e "\n[1/6] 2GB Swap is already configured."
fi

# 2. Install Required System Packages
echo -e "\n[2/6] Updating APT repositories & installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  python3 \
  python3-pip \
  python3-venv \
  git \
  curl \
  wget \
  libgl1 \
  libglib2.0-0 \
  build-essential

# 3. Install Astral UV Package Manager
echo -e "\n[3/6] Installing 'uv' package manager..."
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo "✓ uv version: $(uv --version)"

# 4. Install Cloudflare Tunnel CLI (cloudflared)
echo -e "\n[4/6] Installing cloudflared CLI..."
if ! command -v cloudflared >/dev/null 2>&1; then
  ARCH=$(uname -m)
  if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
  else
    CF_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
  fi
  sudo wget -q -O /usr/local/bin/cloudflared "$CF_URL"
  sudo chmod +x /usr/local/bin/cloudflared
fi
echo "✓ cloudflared installed: $(cloudflared --version)"

# 5. Synchronize Python Environment with PyTorch CPU
echo -e "\n[5/6] Setting up Python 3.12 virtualenv with PyTorch CPU..."
cd "$BACKEND_DIR"

# Install lightweight PyTorch CPU wheels into virtualenv first (avoids CUDA download)
uv venv .venv --python 3.12
uv pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
uv sync

# 6. Configure & Start Systemd Service
echo -e "\n[6/6] Configuring Systemd service 'onion-grading.service'..."
USER_NAME=$(whoami)
SERVICE_FILE="/etc/systemd/system/onion-grading.service"

sudo bash -c "cat << 'EOF' > $SERVICE_FILE
[Unit]
Description=Onion Quality Assessment & Autonomous Grading Backend
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$BACKEND_DIR
ExecStart=$BACKEND_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable onion-grading
sudo systemctl restart onion-grading

echo -e "\nWaiting 5 seconds for service to initialize..."
sleep 5

# Healthcheck
if curl -s http://127.0.0.1:8000/api/health | grep -q "status"; then
  echo -e "\n=================================================================="
  echo "  ✅ Onion Grading is LIVE on http://localhost:8000"
  echo "=================================================================="
  echo "To launch your free Cloudflare HTTPS link for mobile testing, run:"
  echo ""
  echo "  ./deploy/start_tunnel.sh"
  echo "=================================================================="
else
  echo -e "\n[!] Warning: Healthcheck did not immediately respond. Check logs:"
  echo "  sudo journalctl -u onion-grading -n 50 --no-pager"
fi
