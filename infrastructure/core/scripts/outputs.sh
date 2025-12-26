#!/bin/bash

################################################################################
# Display Terraform Outputs
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"

cd "$TF_DIR"

if [ ! -f "terraform.tfstate" ]; then
    echo "No terraform.tfstate found. Run ./deploy.sh first"
    exit 1
fi

echo "Current Infrastructure Outputs:"
echo ""
terraform output

echo ""
echo "To get specific output:"
echo "   terraform output -raw webhook_url"
echo ""