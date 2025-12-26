#!/bin/bash

################################################################################
# Destroy Core Agent Infrastructure
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/../terraform"

echo "⚠️  Destroying Agentic DevOps Healing - Core Infrastructure"
echo ""
echo "This will DELETE all resources including:"
echo "  - Function App"
echo "  - Azure OpenAI"
echo "  - Storage Account (and all logs)"
echo "  - Key Vault (and all secrets)"
echo "  - Application Insights"
echo ""

read -p "Are you SURE you want to destroy? (type 'destroy' to confirm): " confirm

if [ "$confirm" != "destroy" ]; then
    echo "Destruction cancelled"
    exit 0
fi

cd "$TF_DIR"

echo "🗑️  Destroying resources..."
terraform destroy -auto-approve

echo ""
echo "All resources destroyed"
echo "Cost savings: ~$5-10/month"
echo ""