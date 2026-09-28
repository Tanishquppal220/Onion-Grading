#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Grading System
# Mobile Network & Local LAN Development Launcher
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

MODE="http"
if [[ "$1" == "--https" ]]; then
  MODE="https"
fi

# Detect Local LAN IP
detect_ip() {
  local ip=""
  # Try ip route first (most accurate for active default gateway)
  if command -v ip >/dev/null 2>&1; then
    ip=$(ip route get 1.1.1.1 2>/dev/null | awk -F"src " 'NR==1{split($2,a," ");print a[1]}')
  fi
  # Fallback to hostname -I
  if [[ -z "$ip" ]] && command -v hostname >/dev/null 2>&1; then
    ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  fi
  # Fallback to localhost if no network detected
  if [[ -z "$ip" ]]; then
    ip="127.0.0.1"
  fi
  echo "$ip"
}

LAN_IP=$(detect_ip)

echo -e "${BOLD}${GREEN}"
echo "=================================================================="
echo "  🧅 Onion Quality Assessment — Mobile Network Launcher"
echo "=================================================================="
echo -e "${NC}"

# Check UFW Firewall Status
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ufw; then
  if ! grep -q "5173" /etc/ufw/user.rules 2>/dev/null; then
    echo -e "${YELLOW}${BOLD}[!] Firewall Notice:${NC}${YELLOW} UFW is active and port 5173 is not yet explicitly allowed."
    echo -e "    If your phone times out connecting, run this once in another terminal:"
    echo -e "    ${BOLD}sudo ufw allow 5173/tcp${NC}\n"
  fi
fi

if [[ "$MODE" == "https" ]]; then
  PHONE_URL="https://${LAN_IP}:5173/"
  LOCAL_URL="https://localhost:5173/"
  echo -e "  Mode:              ${CYAN}${BOLD}HTTPS (Secure Context Enabled)${NC}"
  echo -e "  ${BOLD}📱 Phone URL:       ${GREEN}${PHONE_URL}${NC}"
  echo -e "  💻 Workstation:    ${BLUE}${LOCAL_URL}${NC}"
  echo -e "  📷 Mobile Camera:   ${BOLD}Live Viewfinder HUD + Torch active${NC}"
  echo -e "  ${YELLOW}(Note: Tap 'Advanced -> Proceed' when self-signed certificate warning appears)${NC}"
else
  PHONE_URL="http://${LAN_IP}:5173/"
  LOCAL_URL="http://localhost:5173/"
  echo -e "  Mode:              ${CYAN}${BOLD}HTTP (Zero-Warning Standard Mode)${NC}"
  echo -e "  ${BOLD}📱 Phone URL:       ${GREEN}${PHONE_URL}${NC}"
  echo -e "  💻 Workstation:    ${BLUE}${LOCAL_URL}${NC}"
  echo -e "  📷 Mobile Camera:   ${BOLD}Tap 'Snap Photo (Phone Camera)' on main screen${NC}"
  echo -e "  ${YELLOW}(To enable real-time Live Viewfinder HUD over HTTPS, pass --https)${NC}"
fi

echo -e "\n  ⚙️ Backend API:     http://localhost:8000/ (proxied via Vite on port 5173)"
echo -e "==================================================================\n"

# Clean shutdown handler
cleanup() {
  echo -e "\n${YELLOW}Shutting down services...${NC}"
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo -e "${GREEN}All services stopped cleanly.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 1. Start Backend if not already running on port 8000
if ss -tulpn 2>/dev/null | grep -q ":8000 "; then
  echo -e "${GREEN}✓ Backend is already running on port 8000.${NC}"
else
  echo -e "${BLUE}Starting FastAPI Backend on port 8000...${NC}"
  cd "$BACKEND_DIR"
  uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
  BACKEND_PID=$!
  sleep 1.5
fi

# 2. Start Frontend
echo -e "${BLUE}Starting Vite Frontend on port 5173...${NC}"
cd "$FRONTEND_DIR"

if [[ "$MODE" == "https" ]]; then
  npm run dev:https &
  FRONTEND_PID=$!
else
  npm run dev &
  FRONTEND_PID=$!
fi

# Keep script running
wait $FRONTEND_PID
