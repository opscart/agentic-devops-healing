#!/bin/bash

echo "🔍 Pre-Deployment Checklist for Agentic DevOps Healing"
echo "======================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Check 1: Azure CLI
echo -n "1. Azure CLI installed... "
if command -v az &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 2: Terraform
echo -n "2. Terraform installed... "
if command -v terraform &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 3: Azure Functions Core Tools
echo -n "3. Azure Functions Core Tools... "
if command -v func &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    ERRORS=$((ERRORS + 1))
fi

# Check 4: Azure Login
echo -n "4. Azure CLI authenticated... "
if az account show &> /dev/null; then
    echo -e "${GREEN}✅${NC}"
    SUBSCRIPTION=$(az account show --query name -o tsv)
    echo "   Subscription: $SUBSCRIPTION"
else
    echo -e "${RED}❌${NC}"
    echo "   Run: az login"
    ERRORS=$((ERRORS + 1))
fi

# Check 5: terraform.tfvars OR environment variables
echo -n "5. Configuration ready... "
if [ -f "terraform.tfvars" ]; then
    echo -e "${GREEN}✅ terraform.tfvars exists${NC}"
elif [ ! -z "$TF_VAR_ado_org_url" ]; then
    echo -e "${GREEN}✅ Environment variables set${NC}"
else
    echo -e "${RED}❌${NC}"
    echo "   Create terraform.tfvars OR set TF_VAR_* environment variables"
    ERRORS=$((ERRORS + 1))
fi

# Check 6: Azure DevOps PAT (optional check)
echo -n "6. Azure DevOps PAT... "
if [ ! -z "$TF_VAR_ado_pat_token" ]; then
    echo -e "${GREEN}✅ Set in environment${NC}"
elif grep -q 'ado_pat_token = ""' terraform.tfvars 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Will need to set in Key Vault after deployment${NC}"
else
    echo -e "${YELLOW}⚠️  Not checked${NC}"
fi

echo ""
echo "======================================================"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo "Next step:"
    echo "  cd infrastructure/core/terraform"
    echo "  ../scripts/deploy.sh"
else
    echo -e "${RED}❌ $ERRORS check(s) failed. Fix issues before deploying.${NC}"
    exit 1
fi