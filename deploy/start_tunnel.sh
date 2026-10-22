#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# Cloudflare Quick Tunnel Launcher
#
# Generates an instant, zero-cost, trusted HTTPS URL with camera access.
# ==============================================================================

set -euo pipefail

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Error: cloudflared is not installed. Run deploy/setup_micro_ec2.sh first."
  exit 1
fi

echo "=================================================================="
echo "  🌐 Starting Free Cloudflare HTTPS Tunnel"
echo "  Forwarding to: http://127.0.0.1:8000"
echo "=================================================================="
echo "Look for the URL ending with .trycloudflare.com below."
echo "Share that URL with your teacher to test on desktop or mobile camera!"
echo "Press Ctrl+C anytime to stop the tunnel."
echo "=================================================================="
echo ""

cloudflared tunnel --url http://127.0.0.1:8000
