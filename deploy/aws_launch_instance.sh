#!/usr/bin/env bash
# ==============================================================================
# Onion Quality Assessment & Autonomous Grading System
# AWS EC2 Instance Launcher (ap-south-1 Mumbai)
#
# Launches an ultra-low-cost micro instance with 10GB gp3 storage.
# Run with AWS admin credentials (e.g. AWS_PROFILE=default or AWS_PROFILE=tanishq-admin)
# ==============================================================================

set -euo pipefail

REGION="${AWS_REGION:-ap-south-1}"
INSTANCE_TYPE="${1:-t3.micro}"
KEY_NAME="${2:-}"

echo "=================================================================="
echo "  🧅 Launching EC2 Micro Instance for Onion Grading"
echo "  Region:        $REGION"
echo "  Instance Type: $INSTANCE_TYPE"
echo "=================================================================="

# Check if AWS CLI is installed
if ! command -v aws >/dev/null 2>&1; then
  echo "Error: AWS CLI is not installed or not in PATH."
  exit 1
fi

# Determine architecture based on instance family
ARCH="amd64"
if [[ "$INSTANCE_TYPE" =~ ^t4g ]]; then
  ARCH="arm64"
fi

# Ensure Key Pair is provided
if [[ -z "$KEY_NAME" ]]; then
  echo ""
  echo "Available Key Pairs in $REGION:"
  aws ec2 describe-key-pairs --region "$REGION" --query 'KeyPairs[*].KeyName' --output table 2>/dev/null || true
  echo ""
  read -rp "Enter your EC2 Key Pair name: " KEY_NAME
  if [[ -z "$KEY_NAME" ]]; then
    echo "Error: Key pair name is required to SSH into the instance."
    exit 1
  fi
fi

# 1. Check or Create Default VPC
echo -e "\n[1/5] Checking Default VPC in $REGION..."
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text 2>/dev/null || true)
if [[ "$VPC_ID" == "None" || -z "$VPC_ID" ]]; then
  echo "Creating default VPC in $REGION..."
  VPC_ID=$(aws ec2 create-default-vpc --region "$REGION" --query "Vpc.VpcId" --output text)
fi
echo "✓ Default VPC ID: $VPC_ID"

# 2. Check or Create Security Group
echo -e "\n[2/5] Configuring Security Group 'onion-micro-sg'..."
SG_ID=$(aws ec2 describe-security-groups --region "$REGION" --filters "Name=group-name,Values=onion-micro-sg" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text 2>/dev/null || true)

if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
  echo "Creating security group 'onion-micro-sg'..."
  SG_ID=$(aws ec2 create-security-group \
    --group-name onion-micro-sg \
    --description "Security group for Onion Grading Micro demo" \
    --vpc-id "$VPC_ID" \
    --region "$REGION" \
    --query "GroupId" --output text)
  
  # Allow SSH from everywhere (or restrict to your IP if desired)
  aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"
  echo "✓ Added SSH ingress rule (port 22)"
fi
echo "✓ Security Group ID: $SG_ID"

# 3. Locate Latest Official Ubuntu 24.04 LTS AMI
echo -e "\n[3/5] Querying latest Ubuntu 24.04 LTS ($ARCH) AMI in $REGION..."
AMI_ID=$(aws ec2 describe-images --region "$REGION" \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-$ARCH-server-*" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' --output text)
echo "✓ AMI ID: $AMI_ID"

# 4. Launch EC2 Instance with 10 GB gp3 storage
echo -e "\n[4/5] Launching $INSTANCE_TYPE instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":10,"VolumeType":"gp3"}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=onion-grading-demo}]' \
  --region "$REGION" \
  --query 'Instances[0].InstanceId' --output text)
echo "✓ Instance launched: $INSTANCE_ID"

# 5. Wait for Public IP
echo -e "\n[5/5] Waiting for instance to obtain public IPv4..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

echo -e "\n=================================================================="
echo "  🚀 Instance Ready!"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP:   $PUBLIC_IP"
echo "=================================================================="
echo "Next step: Connect via SSH and run the setup script:"
echo ""
echo "  ssh -i \"$KEY_NAME.pem\" ubuntu@$PUBLIC_IP"
echo "  git clone -b deploy https://github.com/Tanishquppal220/Onion-Grading.git"
echo "  cd Onion-Grading"
echo "  chmod +x deploy/setup_micro_ec2.sh deploy/start_tunnel.sh"
echo "  ./deploy/setup_micro_ec2.sh"
echo "=================================================================="
