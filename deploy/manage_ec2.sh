#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# EC2 Cost & Lifecycle Management Helper
#
# Commands: start, stop, status, url, ssh, terminate
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.ec2_instance_info.env"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

if [[ ! -f "$ENV_FILE" ]]; then
  echo -e "${YELLOW}Error: Instance configuration file not found at $ENV_FILE${NC}"
  echo "Please run ./deploy/one_click_deploy_aws.sh first to launch an instance."
  exit 1
fi

source "$ENV_FILE"

ACTION="${1:-status}"

get_state() {
  aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" \
    --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null || echo "not-found"
}

get_public_ip() {
  aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' --output text 2>/dev/null || echo ""
}

case "$ACTION" in
  status)
    STATE=$(get_state)
    IP=$(get_public_ip)
    echo -e "${BOLD}Instance Status:${NC}"
    echo -e "  ID:     ${CYAN}$INSTANCE_ID${NC}"
    echo -e "  Region: ${CYAN}$REGION${NC}"
    echo -e "  Type:   ${CYAN}$INSTANCE_TYPE${NC}"
    if [[ "$STATE" == "running" ]]; then
      echo -e "  State:  ${GREEN}${BOLD}$STATE${NC}"
      echo -e "  IP:     ${GREEN}$IP${NC}"
    else
      echo -e "  State:  ${YELLOW}${BOLD}$STATE${NC} (Compute cost: \$0.00/hr)"
    fi
    ;;

  stop)
    STATE=$(get_state)
    if [[ "$STATE" != "running" ]]; then
      echo "Instance is already $STATE."
      exit 0
    fi
    echo -e "${YELLOW}Stopping EC2 instance $INSTANCE_ID...${NC}"
    aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$REGION" >/dev/null
    echo "Waiting for instance to stop..."
    aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID" --region "$REGION"
    echo -e "${GREEN}✓ Instance stopped successfully. Compute billing paused (\$0.00/hr).${NC}"
    ;;

  start)
    STATE=$(get_state)
    if [[ "$STATE" == "running" ]]; then
      echo "Instance is already running."
    else
      echo -e "${BLUE}Starting EC2 instance $INSTANCE_ID...${NC}"
      aws ec2 start-instances --instance-ids "$INSTANCE_ID" --region "$REGION" >/dev/null
      echo "Waiting for instance to enter running state..."
      aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
    fi

    IP=$(get_public_ip)
    echo -e "✓ Instance running at Public IP: ${GREEN}${BOLD}$IP${NC}"

    # Update IP in env file
    sed -i "s/^PUBLIC_IP=.*/PUBLIC_IP=\"$IP\"/" "$ENV_FILE" 2>/dev/null || true

    echo "Ensuring services are running & refreshing Cloudflare tunnel..."
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10 -i "$KEY_FILE" "ubuntu@$IP" \
      'sudo systemctl start onion-grading.service && sudo systemctl restart onion-tunnel.service' || true
    
    echo -e "\nFetching new live HTTPS URL..."
    for i in {1..15}; do
      URL=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -i "$KEY_FILE" "ubuntu@$IP" \
        "grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /var/log/cloudflared.log | tail -n 1 2>/dev/null" || true)
      if [[ -n "$URL" ]]; then
        echo -e "\n  📱 ${BOLD}${GREEN}LIVE HTTPS URL:${NC} ${CYAN}${BOLD}$URL${NC}\n"
        ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -i "$KEY_FILE" "ubuntu@$IP" \
          "echo '$URL' > /home/ubuntu/TUNNEL_URL.txt" 2>/dev/null || true
        break
      fi
      sleep 2
    done
    ;;

  url)
    STATE=$(get_state)
    if [[ "$STATE" != "running" ]]; then
      echo -e "${YELLOW}Instance is currently $STATE. Run './deploy/manage_ec2.sh start' first.${NC}"
      exit 1
    fi
    IP=$(get_public_ip)
    echo "Querying live tunnel URL from instance..."
    URL=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=6 -i "$KEY_FILE" "ubuntu@$IP" \
      "grep -o 'https://[-a-zA-Z0-9.]*\.trycloudflare\.com' /var/log/cloudflared.log | tail -n 1 2>/dev/null" || true)
    if [[ -n "$URL" ]]; then
      echo -e "  📱 ${BOLD}${GREEN}LIVE HTTPS URL:${NC} ${CYAN}${BOLD}$URL${NC}"
    else
      echo "Could not fetch URL. Make sure onion-tunnel.service is running."
    fi
    ;;

  ssh)
    STATE=$(get_state)
    if [[ "$STATE" != "running" ]]; then
      echo -e "${YELLOW}Instance is currently $STATE. Run './deploy/manage_ec2.sh start' first.${NC}"
      exit 1
    fi
    IP=$(get_public_ip)
    echo "Connecting to ubuntu@$IP..."
    exec ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "ubuntu@$IP"
    ;;

  terminate)
    echo -e "${YELLOW}${BOLD}WARNING: This will permanently destroy the EC2 instance ($INSTANCE_ID)!${NC}"
    read -rp "Are you sure you want to terminate? (type 'yes' to proceed): " CONFIRM
    if [[ "$CONFIRM" == "yes" ]]; then
      aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" --region "$REGION" >/dev/null
      echo -e "${GREEN}✓ Instance $INSTANCE_ID termination initiated.${NC}"
      rm -f "$ENV_FILE"
      echo "Cleaned up local metadata."
    else
      echo "Termination canceled."
    fi
    ;;

  *)
    echo "Usage: ./deploy/manage_ec2.sh {status|start|stop|url|ssh|terminate}"
    exit 1
    ;;
esac
