# Deploy Core Infrastructure

This guide walks you through deploying the agent infrastructure to Azure.

---

## What Gets Deployed

Running `deploy.sh` will create:
```
Azure Resources (Region: eastus):
├── Resource Group
│   └── rg-agenticdevops-dev
│
├── Storage Account (for Functions + logs)
│   ├── Name: stagenticdevopsXXXXXX (random 6-char suffix)
│   ├── Containers:
│   │   ├── build-logs (pipeline failure logs)
│   │   └── tfstate (Terraform state for test apps)
│   └── Queue: pipeline-failures (for async processing)
│
├── Function App (the AI agent)
│   ├── Name: func-agenticdevops-XXXXXX
│   ├── Runtime: Python 3.11
│   ├── Plan: Consumption (Y1) - pay per execution
│   └── System-Assigned Managed Identity
│
├── Azure OpenAI
│   ├── Name: oai-agenticdevops-XXXXXX
│   ├── Model Deployment: gpt-4o-analyzer
│   │   ├── Model: GPT-4o (2024-11-20)
│   │   └── Capacity: 10K tokens/min
│
├── Key Vault (secrets storage)
│   ├── Name: kv-agenticdevops-XXXXXX
│   ├── Secrets:
│   │   ├── openai-api-key (auto-populated)
│   │   └── ado-pat (you'll set this manually)
│   └── Access: Function App via Managed Identity
│
├── Application Insights (monitoring)
│   ├── Name: appi-agenticdevops-dev
│   └── Connected to: Log Analytics Workspace
│
└── Log Analytics Workspace
    └── Name: log-agenticdevops-dev
```

**Deployment time:** ~5-10 minutes  
**Initial cost:** ~$5/month baseline

---

## 🚀 Deployment Steps

### Step 1: Navigate to Terraform Directory
```bash
cd infrastructure/core/terraform
```

### Step 2: Create `terraform.tfvars`
```bash
# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required values to update:**
```hcl
# infrastructure/core/terraform/terraform.tfvars

resource_prefix = "agenticdevops"  # Keep as-is or customize
environment     = "dev"
azure_region    = "eastus"         # Or your preferred region
openai_region   = "eastus"         # Must support OpenAI

# Azure DevOps Settings
ado_org_url      = "https://dev.azure.com/YOUR_ORG"  # UPDATE THIS
ado_project_name = "YOUR_PROJECT"                     # UPDATE THIS

# DON'T set ado_pat_token here - we'll set it in Key Vault after deployment
# ado_pat_token = ""

common_tags = {
  Project     = "Agentic DevOps Healing"
  ManagedBy   = "Terraform"
  Environment = "dev"
  Owner       = "Shamsher Khan"
  CostCenter  = "Research"
}
```

**Save and exit:** `Ctrl+X`, `Y`, `Enter`

### Step 3: Verify Azure Login
```bash
# Check current subscription
az account show

# Output should show:
# {
#   "id": "your-subscription-id",
#   "name": "your-subscription-name",
#   "state": "Enabled",
#   ...
# }

# If not logged in:
az login

# If wrong subscription:
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### Step 4: Run Deployment Script
```bash
# Make script executable (if not already)
chmod +x ../scripts/deploy.sh

# Run deployment
../scripts/deploy.sh
```

**What the script does:**

1. Checks prerequisites (Terraform, Azure CLI)
2. Verifies Azure login
3. Checks for `terraform.tfvars`
4. Initializes Terraform
5. Validates configuration
6. Shows deployment plan
7. Asks for confirmation
8. Deploys resources (5-10 minutes)
9. Saves outputs to `outputs.json`
10. Displays next steps

### Step 5: Review Deployment Plan

Terraform will show what it will create:
```
Terraform will perform the following actions:

  # azurerm_resource_group.main will be created
  + resource "azurerm_resource_group" "main" {
      + id       = (known after apply)
      + location = "eastus"
      + name     = "rg-agenticdevops-dev"
    }

  # azurerm_storage_account.main will be created
  ...

  # azurerm_linux_function_app.main will be created
  ...

Plan: 11 to add, 0 to change, 0 to destroy.
```

**Review carefully!** Check:
- Resource names look correct
- Region is what you want
- No unexpected resources

### Step 6: Confirm Deployment
```
Deploy these resources? (yes/no):
```

Type: **`yes`**

### Step 7: Wait for Deployment
```
Deploying...

azurerm_resource_group.main: Creating...
azurerm_resource_group.main: Creation complete after 2s
random_string.suffix: Creating...
random_string.suffix: Creation complete after 0s
azurerm_storage_account.main: Creating...
azurerm_log_analytics_workspace.main: Creating...
...
azurerm_linux_function_app.main: Still creating... [1m30s elapsed]
azurerm_cognitive_account.openai: Still creating... [2m0s elapsed]
...

Apply complete! Resources: 11 added, 0 changed, 0 destroyed.
```

**Deployment typically takes 5-10 minutes**

Most time is spent on:
- Azure OpenAI creation: ~3-5 minutes
- Function App creation: ~2-3 minutes

---

## ✅ Post-Deployment Steps

### Step 1: Review Outputs

After deployment completes, you'll see:
```
Outputs:

resource_group_name = "rg-agenticdevops-dev"
function_app_name = "func-agenticdevops-abc123"
webhook_url = "https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure"
storage_account_name = "stagenticdevopsabc123"
key_vault_name = "kv-agenticdevops-abc123"
openai_endpoint = "https://oai-agenticdevops-abc123.openai.azure.com/"
openai_deployment_name = "gpt-4o-analyzer"

✅ Deployment Complete!

📋 Next Steps:

1. Set Azure DevOps PAT in Key Vault:
   az keyvault secret set --vault-name kv-agenticdevops-abc123 \
     --name ado-pat --value "YOUR_AZURE_DEVOPS_PAT"

2. Deploy Function App code:
   cd ../../../src/agents/infra-healer
   func azure functionapp publish func-agenticdevops-abc123

3. Get Function Key:
   func azure functionapp list-functions func-agenticdevops-abc123 --show-keys

4. Update Azure DevOps pipeline with webhook:
   https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=YOUR_FUNCTION_KEY

5. View logs:
   func azure functionapp logstream func-agenticdevops-abc123
```

**Save these outputs!** You'll need them for next steps.

### Step 2: Set Azure DevOps PAT in Key Vault
```bash
# Get your PAT from Azure DevOps
# (Created in previous step: docs/setup/01-azure-prerequisites.md)

# Set it in Key Vault
az keyvault secret set \
  --vault-name kv-agenticdevops-abc123 \
  --name ado-pat \
  --value "YOUR_ACTUAL_PAT_TOKEN_HERE"

# Verify it was set
az keyvault secret show \
  --vault-name kv-agenticdevops-abc123 \
  --name ado-pat \
  --query "value" -o tsv
```

⚠️ **Replace `kv-agenticdevops-abc123`** with your actual Key Vault name from outputs!

### Step 3: Deploy Function App Code

Now we need to deploy the actual Python code to the Function App:
```bash
# Navigate to agent source code
cd ../../../src/agents/infra-healer

# Install dependencies locally (for testing)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Deploy to Azure
func azure functionapp publish func-agenticdevops-abc123

# You should see:
# Getting site publishing info...
# Uploading package...
# Upload completed successfully.
# Deployment completed successfully.
# Syncing triggers...
# Functions in func-agenticdevops-abc123:
#     HandleFailure - [httpTrigger]
#         Invoke url: https://func-agenticdevops-abc123.azurewebsites.net/api/handlefailure
```

⚠️ **Replace `func-agenticdevops-abc123`** with your actual Function App name!

### Step 4: Get Function Key (for webhooks)
```bash
# Get the function key needed for webhook authentication
func azure functionapp list-functions func-agenticdevops-abc123 --show-keys

# Output:
# Functions in func-agenticdevops-abc123:
#
# HandleFailure - [httpTrigger]
#     Invoke url: https://func-agenticdevops-abc123.azurewebsites.net/api/handlefailure
#     Function Keys:
#       default: xyz123abc456def789...
```

**Copy the function key** - you'll need it for Azure DevOps pipeline configuration.

### Step 5: Test the Function
```bash
# Test that the function is responding
curl -X POST \
  "https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=YOUR_FUNCTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "pipelineId": "123",
    "buildId": "456",
    "buildNumber": "20241225.1",
    "projectName": "test-project",
    "failedStage": "Build",
    "failedJob": "TerraformApply"
  }'

# Expected response (HTTP 202):
# {
#   "status": "success",
#   "failure_context": { ... },
#   "rca": { ... },
#   "action_taken": "RCA_COMMENT_POSTED"
# }
```

If you get an error about missing ADO connection, that's normal - we haven't configured Azure DevOps pipeline yet.

---

## Verify Deployment

### Check Resources in Azure Portal
```bash
# Open resource group in portal
az group show --name rg-agenticdevops-dev --query "id" -o tsv | \
  xargs -I {} echo "https://portal.azure.com/#@/resource{}/overview"

# Or list all resources
az resource list --resource-group rg-agenticdevops-dev --output table
```

**Expected resources:**

| Name | Type | Status |
|------|------|--------|
| func-agenticdevops-* | Function App | Running |
| st-agenticdevops-* | Storage Account | Available |
| kv-agenticdevops-* | Key Vault | Available |
| oai-agenticdevops-* | Cognitive Services (OpenAI) | Succeeded |
| appi-agenticdevops-dev | Application Insights | Active |
| log-agenticdevops-dev | Log Analytics | Active |
| asp-agenticdevops-dev | App Service Plan | Running |

### Check Function App Logs
```bash
# Stream live logs
func azure functionapp logstream func-agenticdevops-abc123

# You should see:
# 2024-12-25T10:00:00.000 [Information] Executing 'Functions.HandleFailure' (Reason='This function was programmatically called via the host APIs.', Id=...)
# 2024-12-25T10:00:00.123 [Information] Function "HandleFailure" ready
```

Press `Ctrl+C` to stop streaming.

### Check Application Insights
```bash
# Open Application Insights in portal
echo "https://portal.azure.com/#@/resource/subscriptions/YOUR_SUB/resourceGroups/rg-agenticdevops-dev/providers/microsoft.insights/components/appi-agenticdevops-dev/overview"

# Or query recent traces
az monitor app-insights query \
  --app appi-agenticdevops-dev \
  --resource-group rg-agenticdevops-dev \
  --analytics-query "traces | where timestamp > ago(1h) | limit 10"
```

---

## Current Cost

After deployment, you're now paying:
```
Daily Cost (approximation):
├── Function App (Consumption): $0.00 (no executions yet)
├── Storage Account: $0.10
├── OpenAI: $0.00 (no API calls yet)
├── Key Vault: $0.001
├── App Insights: $0.00 (under free tier)
└── Log Analytics: $0.00 (under free tier)

Total: ~$0.10-0.15/day = ~$3-5/month baseline
```

**Usage costs** (when testing):
- Each failure analysis: ~$0.05-0.10
- 100 tests: ~$5-10

---

## 🔧 Troubleshooting

### Issue: Terraform Init Fails
```bash
Error: Failed to query available provider packages
```

**Solution:**
```bash
# Clear Terraform cache
rm -rf .terraform .terraform.lock.hcl

# Re-initialize
terraform init
```

### Issue: OpenAI Deployment Fails
```
Error: creating Cognitive Deployment: Access Denied
```

**Solution:**
Your OpenAI access request is still pending. Two options:

1. **Wait for approval** (check email)
2. **Skip OpenAI for now:**
```bash
   # Comment out OpenAI resources in main.tf
   # Lines 95-120 (azurerm_cognitive_account, azurerm_cognitive_deployment)
   
   # Deploy without OpenAI
   terraform apply
   
   # Add OpenAI later when approved
```

### Issue: Function App Publish Fails
```
Error: Failed to get publishing credentials
```

**Solution:**
```bash
# Restart Function App
az functionapp restart --name func-agenticdevops-abc123 --resource-group rg-agenticdevops-dev

# Wait 30 seconds, then try publish again
func azure functionapp publish func-agenticdevops-abc123
```

### Issue: Key Vault Access Denied
```
Error: The user does not have secrets get permission
```

**Solution:**
```bash
# Grant yourself access
az keyvault set-policy \
  --name kv-agenticdevops-abc123 \
  --upn YOUR_EMAIL@example.com \
  --secret-permissions get list set delete
```

### Issue: Can't Find Outputs
```bash
# If you closed terminal and lost outputs, retrieve them:
cd infrastructure/core/terraform

# View all outputs
terraform output

# Get specific output
terraform output -raw webhook_url
terraform output -raw function_app_name
terraform output -raw key_vault_name

# Or use the outputs script
../scripts/outputs.sh
```

---

## Success Checklist

Before moving to next step, verify:

- [ ] All 11 resources created successfully
- [ ] Function App is running
- [ ] Function code deployed (HandleFailure function exists)
- [ ] Azure DevOps PAT set in Key Vault
- [ ] Function key retrieved
- [ ] Test webhook responded successfully
- [ ] Application Insights showing function telemetry
- [ ] No deployment errors in portal

---

## How to Destroy (If Needed)

If you want to tear down everything:
```bash
cd infrastructure/core/terraform

# Run destroy script
../scripts/destroy.sh

# Confirm by typing: destroy

# Resources will be deleted in reverse order
# Takes ~3-5 minutes
```

**What gets deleted:**
- Function App
- Storage Account (and all logs)
- Azure OpenAI
- Key Vault (and all secrets)
- Application Insights
- Log Analytics Workspace
- Resource Group

**What survives:**
- Terraform state file (local: `terraform.tfstate`)
- Your source code
- Configuration files

**To redeploy later:**
```bash
# Just run deploy again
../scripts/deploy.sh
```

---

## Next Steps

Infrastructure is now deployed! ✅

**Next:** Configure Azure DevOps pipeline to call the agent

👉 See: `docs/setup/03-configure-ado.md`

Or test with a simple scenario first:

👉 See: `docs/setup/04-test-first-scenario.md`

---

## Save Important Values

**Keep these for reference:**
```bash
# Function App Name
func-agenticdevops-abc123

# Webhook URL
https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure

# Function Key
xyz123abc456...

# Key Vault Name
kv-agenticdevops-abc123

# Resource Group
rg-agenticdevops-dev

# Full webhook URL with key
https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=xyz123abc456...
```

Copy these to a safe place (password manager, encrypted notes, etc.)

---

## 💡 Cost Management Reminder

### Daily Costs
```
Current state (idle): ~$0.10-0.15/day
With testing: ~$0.50-1.00/day
```

### To Minimize Costs

**Option 1: Keep running** (if testing daily)
- Cost: ~$5-10/month baseline
- Ready anytime

**Option 2: Destroy when not testing** (if testing weekly)
```bash
# Friday evening
../scripts/destroy.sh

# Monday morning
../scripts/deploy.sh
```
- Cost: $0 when destroyed
- 10 minutes to redeploy

**My recommendation for your timeline:**
- Week 1-2: Keep up (active development)
- Week 3-4: Keep up (testing scenarios)
- Between weeks: Destroy
- **Total project cost: $40-80**

---

## Deployment Complete!

Your agent infrastructure is now live and ready to heal pipelines! 🎉

**What you have:**
- Function App receiving webhooks
- Azure OpenAI analyzing failures
- Storage for logs
- Key Vault for secrets
- Monitoring via App Insights

**What's next:**
1. Configure Azure DevOps pipeline
2. Test with first scenario
3. Iterate and improve

Let's go! 🚀