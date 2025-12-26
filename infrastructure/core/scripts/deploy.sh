#!/bin/bash

################################################################################
# Deploy Core Agent Infrastructure
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"

echo "🚀 Deploying Agentic DevOps Healing - Core Infrastructure"
echo ""

# Check prerequisites
command -v terraform >/dev/null 2>&1 || { echo "Terraform not installed"; exit 1; }
command -v az >/dev/null 2>&1 || { echo "Azure CLI not installed"; exit 1; }

# Check Azure login
az account show >/dev/null 2>&1 || { echo "Not logged into Azure. Run: az login"; exit 1; }

echo "Prerequisites check passed"
echo ""

cd "$TF_DIR"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "⚠️  terraform.tfvars not found"
    echo "Creating from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo ""
    echo "❗ Please edit terraform.tfvars with your values:"
    echo "   - ado_org_url"
    echo "   - ado_project_name"
    echo ""
    read -p "Press Enter after updating terraform.tfvars..."
fi

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init

# Validate
echo "Validating configuration..."
terraform validate

# Plan
echo "Planning deployment..."
terraform plan -out=tfplan

# Confirm
echo ""
read -p "Deploy these resources? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Apply
echo "🚀 Deploying..."
terraform apply tfplan

# Clean up plan file
rm -f tfplan

echo ""
echo "Deployment complete!"
echo ""

# Show outputs
terraform output -json > outputs.json
echo "Outputs saved to outputs.json"
echo ""

# Show next steps
terraform output next_steps

echo ""
echo "To view outputs anytime: ./scripts/outputs.sh"
echo ""