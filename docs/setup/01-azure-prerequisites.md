# Azure Prerequisites

This guide walks through setting up your Azure environment for the Agentic DevOps Healing project.

## 📋 What You'll Need

### 1. Azure Account

**Option A: Free Account (Recommended for POC)**
- Visit: https://azure.microsoft.com/free/
- Get $200 credit for 30 days
- 12 months of free services
- No credit card required for first 30 days

**Option B: Pay-As-You-Go**
- Estimated cost: $15-25/month for this experiment
- Full access to all services

**Option C: Visual Studio Subscription**
- $50-150/month recurring credit
- Check: https://my.visualstudio.com/benefits

### 2. Required Tools
```bash
# Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Azure Functions Core Tools
wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4

# Python 3.11
sudo apt install python3.11 python3.11-venv
```

### 3. Azure DevOps

- Organization: https://dev.azure.com
- Create a project or use existing
- Will need PAT (Personal Access Token) later

---

## 🚀 Step-by-Step Setup

### Step 1: Login to Azure
```bash
# Login
az login

# List subscriptions
az account list --output table

# Set active subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify
az account show
```

### Step 2: Request Azure OpenAI Access

Azure OpenAI requires approval:
```bash
# Visit the request form
open https://aka.ms/oai/access

# Fill out:
# - Use case: "Research - AI-powered DevOps automation"
# - Organization: Your company/personal
# - Expected usage: "Experimental research project"

# Approval usually takes 1-2 business days
```

**While waiting for approval**, you can still:
- Deploy infrastructure (it will create OpenAI resource)
- Set up Function App
- Configure Azure DevOps

### Step 3: Create Azure DevOps PAT

1. Go to: https://dev.azure.com/YOUR_ORG/_usersSettings/tokens
2. Click "New Token"
3. Name: `agentic-devops-healing`
4. Scopes:
   - ✅ Build: Read & Execute
   - ✅ Code: Read & Write
   - ✅ Pull Request Threads: Read & Write
   - ✅ Work Items: Read, Write & Manage
5. Expiration: 90 days (you can renew later)
6. **Save the token securely** - you'll need it during deployment

---

## 💰 Cost Breakdown

### Resources Created

| Resource | SKU | Purpose | Monthly Cost |
|----------|-----|---------|--------------|
| Function App | Consumption (Y1) | Agent runtime | ~$0 (free tier) |
| Storage Account | Standard LRS | Logs, state | ~$3 |
| Azure OpenAI | S0 | AI analysis | ~$0 + usage |
| Key Vault | Standard | Secrets | ~$0.03 |
| App Insights | Pay-as-you-go | Monitoring | ~$0-2 |
| Log Analytics | Pay-as-you-go | Logs | ~$0-2 |

**Total baseline: ~$5-10/month**

### Usage Costs

**Azure OpenAI (pay per use):**
- GPT-4o: $2.50 per 1M input tokens, $10 per 1M output tokens
- Average failure analysis: ~5K tokens = $0.06
- 100 failures/month: ~$6
- 500 failures/month: ~$30

**Estimated total: $15-40/month depending on usage**

---

## Important Notes

### Regions

Not all Azure regions support OpenAI. Recommended regions:
- ✅ `eastus`
- ✅ `eastus2`
- ✅ `westus`
- ✅ `swedencentral`

Check current availability: https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models

### Quotas

Free tier quotas:
- OpenAI: 10K tokens/minute (TPM)
- Storage: 5GB
- Functions: 1M executions/month

For this experiment, free tier is sufficient.

---

## Verification Checklist

Before deploying infrastructure:

- [ ] Azure CLI installed and logged in
- [ ] Terraform installed (version >= 1.5)
- [ ] Azure Functions Core Tools installed
- [ ] Python 3.11 installed
- [ ] Azure subscription selected
- [ ] Azure OpenAI access requested (or approved)
- [ ] Azure DevOps PAT created
- [ ] Chosen Azure region (default: eastus)

---

## Next Steps

Once prerequisites are complete:
```bash
# Navigate to infrastructure directory
cd infrastructure/core/terraform

# Copy and customize variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your values

# Proceed to deployment
# See: docs/setup/02-deploy-core-infra.md
```

---

## Troubleshooting

### Azure CLI login issues
```bash
# Clear credentials
az account clear

# Login with device code (works better in some environments)
az login --use-device-code
```

### OpenAI access denied
- Check email for approval/denial
- May need to use corporate email
- Alternative: Use OpenAI API directly (requires code changes)

### Quota issues
- Free accounts have some service restrictions
- Upgrade to Pay-As-You-Go if needed
- Most restrictions don't affect this project
```

---

## Resources Created Summary

When you run `deploy.sh`, these resources will be created:
```
Resource Group: rg-agenticdevops-dev
├── Storage Account: stagenticdevopsXXXXXX
│   ├── Container: build-logs
│   ├── Container: tfstate
│   └── Queue: pipeline-failures
├── Function App: func-agenticdevops-XXXXXX
│   └── Managed Identity (for Key Vault access)
├── App Service Plan: asp-agenticdevops-dev (Consumption)
├── Azure OpenAI: oai-agenticdevops-XXXXXX
│   └── Deployment: gpt-4o-analyzer (GPT-4o model)
├── Key Vault: kv-agenticdevops-XXXXXX
│   ├── Secret: openai-api-key
│   └── Secret: ado-pat
├── Log Analytics: log-agenticdevops-dev
└── Application Insights: appi-agenticdevops-dev