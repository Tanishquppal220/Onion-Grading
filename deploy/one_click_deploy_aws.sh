#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# 1-CLICK AUTOMATED AWS CLI DEPLOYMENT SCRIPT
#
# Region: ap-south-1 (Mumbai)
# Creates VPC, Security Group, Key Pair, and launches EC2 with Cloud-Init.
# Zero manual console actions needed!
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

REGION="${AWS_REGION:-ap-south-1}"
INSTANCE_TYPE="t3.micro" # Default: 100% Free under AWS 12-Month Free Tier
KEY_NAME="onion-grading-key"
KEY_FILE="$SCRIPT_DIR/${KEY_NAME}.pem"
ENV_FILE="$SCRIPT_DIR/.ec2_instance_info.env"

# Parse CLI flags
for arg in "$@"; do
  case $arg in
    --arm|--t4g)
      INSTANCE_TYPE="t4g.micro"
      shift
      ;;
    --t3-small)
      INSTANCE_TYPE="t3.small"
      shift
      ;;
    --t4g-small)
      INSTANCE_TYPE="t4g.small"
      shift
      ;;
    --help|-h)
      echo "Usage: ./deploy/one_click_deploy_aws.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --arm, --t4g     Launch ARM64 Graviton2 instance (t4g.micro, ~\$4.08/mo)"
      echo "  --t3-small       Launch 2GB RAM Intel instance (t3.small)"
      echo "  --t4g-small      Launch 2GB RAM Graviton2 instance (t4g.small, ~\$8.17/mo)"
      echo "  --help, -h       Show this help message"
      exit 0
      ;;
  esac
done

echo -e "${BOLD}${GREEN}"
echo "=================================================================="
echo "  🧅 1-CLICK AUTOMATED EC2 DEPLOYMENT FOR ONION GRADING"
echo "  Region:        ${CYAN}$REGION (Mumbai)${GREEN}"
echo "  Instance Type: ${CYAN}$INSTANCE_TYPE${GREEN}"
echo "=================================================================="
echo -e "${NC}"

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
  echo -e "${YELLOW}Error: AWS CLI is not installed or not in your PATH.${NC}"
  echo "Please install AWS CLI and configure credentials before running."
  exit 1
fi

# Show Active Caller Identity
echo -e "${BLUE}[1/7] Checking AWS credentials...${NC}"
CALLER_JSON=$(aws sts get-caller-identity 2>&1) || {
  echo -e "${YELLOW}Error authenticating with AWS:${NC}"
  echo "$CALLER_JSON"
  echo ""
  echo "Tip: Run 'aws configure' or set AWS_PROFILE=your-profile"
  exit 1
}
CALLER_ARN=$(echo "$CALLER_JSON" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4 || echo "unknown")
echo -e "✓ Authenticated as: ${BOLD}$CALLER_ARN${NC}"

# Determine CPU architecture
ARCH="amd64"
if [[ "$INSTANCE_TYPE" =~ ^t4g ]]; then
  ARCH="arm64"
fi

# Step 2: Ensure Default VPC in ap-south-1
echo -e "\n${BLUE}[2/7] Ensuring Default VPC in $REGION...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text 2>/dev/null || true)
if [[ "$VPC_ID" == "None" || -z "$VPC_ID" ]]; then
  echo "Default VPC not found. Creating default VPC in $REGION..."
  VPC_ID=$(aws ec2 create-default-vpc --region "$REGION" --query "Vpc.VpcId" --output text)
fi
echo -e "✓ Default VPC ID: ${CYAN}$VPC_ID${NC}"

# Step 3: Security Group
echo -e "\n${BLUE}[3/7] Setting up Security Group 'onion-micro-sg'...${NC}"
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=onion-micro-sg" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
  SG_ID=$(aws ec2 create-security-group \
    --group-name onion-micro-sg \
    --description "Security group for Onion Grading Micro demo" \
    --vpc-id "$VPC_ID" \
    --region "$REGION" \
    --query "GroupId" --output text)
  
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region "$REGION" >/dev/null
  echo "✓ Created security group and allowed SSH (port 22)"
else
  echo "✓ Using existing security group: $SG_ID"
fi

# Step 4: Key Pair
echo -e "\n${BLUE}[4/7] Checking SSH Key Pair...${NC}"
KEY_EXISTS_AWS=$(aws ec2 describe-key-pairs --region "$REGION" --filters "Name=key-name,Values=$KEY_NAME" --query "KeyPairs[0].KeyName" --output text 2>/dev/null || true)

if [[ ! -f "$KEY_FILE" ]]; then
  if [[ "$KEY_EXISTS_AWS" != "None" && -n "$KEY_EXISTS_AWS" ]]; then
    echo "Notice: Key pair '$KEY_NAME' already exists in AWS, but local file '$KEY_FILE' is missing."
    echo "Creating a new timestamped key pair to ensure you have the private key..."
    KEY_NAME="onion-key-$(date +%s)"
    KEY_FILE="$SCRIPT_DIR/${KEY_NAME}.pem"
  fi
  echo "Creating new key pair '$KEY_NAME'..."
  aws ec2 create-key-pair --key-name "$KEY_NAME" --region "$REGION" --query 'KeyMaterial' --output text > "$KEY_FILE"
  chmod 400 "$KEY_FILE"
  echo "✓ Saved private key to: $KEY_FILE"
else
  echo "✓ Found local key pair: $KEY_FILE"
fi

# Step 5: Locate AMI
echo -e "\n${BLUE}[5/7] Querying latest official Ubuntu 24.04 LTS ($ARCH) AMI...${NC}"
AMI_ID=$(aws ec2 describe-images --region "$REGION" \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-$ARCH-server-*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text)
echo -e "✓ AMI ID: ${CYAN}$AMI_ID${NC}"

# Step 6: Launch Instance with Cloud-Init User Data
echo -e "\n${BLUE}[6/7] Launching EC2 instance with automated Cloud-Init bootstrap...${NC}"
USER_DATA_FILE="$SCRIPT_DIR/cloud_init_bootstrap.sh"
if [[ ! -f "$USER_DATA_FILE" ]]; then
  echo "Error: $USER_DATA_FILE not found."
  exit 1
fi

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --user-data "file://$USER_DATA_FILE" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":15,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=onion-grading-demo}]' \
  --region "$REGION" \
  --query 'Instances[0].InstanceId' --output text)

echo -e "✓ Instance launched: ${CYAN}$INSTANCE_ID${NC}"

# Save environment for manage_ec2.sh
cat << EOF > "$ENV_FILE"
INSTANCE_ID="$INSTANCE_ID"
REGION="$REGION"
KEY_NAME="$KEY_NAME"
KEY_FILE="$KEY_FILE"
INSTANCE_TYPE="$INSTANCE_TYPE"
EOF

# Step 7: Wait for Public IP and Bootstrap Completion
echo -e "\n${BLUE}[7/7] Waiting for instance to start and obtain public IP...${NC}"
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo -e "✓ Public IP: ${GREEN}${BOLD}$PUBLIC_IP${NC}"
echo "PUBLIC_IP=\"$PUBLIC_IP\"" >> "$ENV_FILE"

echo -e "\n${YELLOW}Waiting for automated Cloud-Init setup to complete (takes ~2 minutes)...${NC}"
echo "Cloud-init is installing packages, PyTorch CPU, and launching Cloudflare Tunnel..."

TUNNEL_URL=""
MAX_ATTEMPTS=45
for ((i=1; i<=MAX_ATTEMPTS; i++)); do
  echo -ne "  [Attempt $i/$MAX_ATTEMPTS] Checking tunnel status...\r"
  
  # Try SSH to check if BOOTSTRAP_COMPLETE exists
  FETCHED_URL=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -o LogLevel=ERROR -i "$KEY_FILE" "ubuntu@$PUBLIC_IP" 'cat /home/ubuntu/TUNNEL_URL.txt 2>/dev/null' || true)
  
  if [[ "$FETCHED_URL" =~ trycloudflare\.com ]]; then
    TUNNEL_URL="$FETCHED_URL"
    echo ""
    break
  fi
  sleep 6
done

echo ""
echo -e "${BOLD}${GREEN}"
echo "=================================================================="
echo "  🎉 ONION QUALITY ASSESSMENT SYSTEM IS LIVE!"
echo "=================================================================="
echo -e "${NC}"
echo -e "  📍 AWS Region:       ${CYAN}$REGION (Mumbai)${NC}"
echo -e "  🖥️  Instance ID:      ${CYAN}$INSTANCE_ID${NC} ($INSTANCE_TYPE)"
echo -e "  🌐 Public IP:        ${CYAN}$PUBLIC_IP${NC}"
echo -e "  🔑 SSH Command:      ${BOLD}ssh -i \"$KEY_FILE\" ubuntu@$PUBLIC_IP${NC}"
echo ""

if [[ -n "$TUNNEL_URL" ]]; then
  echo -e "  📱 ${BOLD}${GREEN}MOBILE CAMERA & DEMO HTTPS URL:${NC}"
  echo -e "  👉 ${BOLD}${CYAN}$TUNNEL_URL${NC}"
  echo ""
  echo "  Share this link with your teacher! They can open it on their"
  echo "  smartphone to access the Live Viewfinder HUD with full camera and torch."
else
  echo -e "  ${YELLOW}Notice: Cloud-init is still finalizing in the background.${NC}"
  echo "  To view your live URL in 30 seconds, run:"
  echo -e "  ${BOLD}./deploy/manage_ec2.sh url${NC}"
fi

echo -e "\n=================================================================="
echo -e "  💡 COST CONTROL TIP:"
echo -e "  When not demonstrating, stop the instance to pay \$0 compute:"
echo -e "    ${BOLD}./deploy/manage_ec2.sh stop${NC}"
echo -e "  Restart it anytime before presenting:"
echo -e "    ${BOLD}./deploy/manage_ec2.sh start${NC}"
echo "=================================================================="
