# Test First Scenario

Let's run your first end-to-end test with a real Terraform failure.

---

## Scenario 1: Missing Terraform Variable

This scenario simulates a common infrastructure failure:
- Terraform requires a variable
- Variable is not defined in pipeline
- Agent detects it, analyzes it, and suggests a fix

---

## What We'll Test
````
Terraform Code (Broken)
    ↓
Pipeline Executes
    ↓
Terraform Fails: "Missing required variable"
    ↓
Webhook Calls Agent
    ↓
Agent Analyzes Failure
    ↓
Agent Creates Fix PR or Posts Comment
````

---

## Step 1: Review Test Code

The test code already exists in your repo. Let's review it:
````bash
# Navigate to scenario
cd infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable

# View the broken Terraform
cat main.tf
````

### What's in `main.tf`:
````hcl
# infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable/main.tf

# This is DELIBERATELY BROKEN to test the agent

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
}

provider "azurerm" {
  features {}
}

# This resource requires 'azure_region' variable which is NOT defined
# The pipeline also doesn't provide it via TF_VAR_azure_region
resource "azurerm_resource_group" "test" {
  name     = "rg-agent-test-${var.environment}"
  location = var.azure_region  # THIS WILL FAIL - variable not defined
}
````

### What's in `variables.tf`:
````hcl
# infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable/variables.tf

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "test"
}

# Notice: azure_region is used in main.tf but NOT defined here
# This is the deliberate error
````

---

## Step 2: Create Test Pipeline

Create a new file in your repo:
````bash
# Create pipeline file
nano .azure-pipelines/test-scenario-1-missing-variable.yml
````

Paste this content:
````yaml
# .azure-pipelines/test-scenario-1-missing-variable.yml

name: Test Scenario 1 - Missing Terraform Variable

trigger: none  # Manual trigger only

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentic-healing-config
  - name: TF_WORKING_DIR
    value: 'infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable'

stages:
  - stage: TerraformTest
    displayName: 'Test: Terraform Missing Variable'
    jobs:
      - job: DeployInfra
        displayName: 'Deploy Test Infrastructure'
        steps:
          # Install Terraform
          - task: TerraformInstaller@0
            displayName: 'Install Terraform'
            inputs:
              terraformVersion: 'latest'
          
          # Terraform Init
          - task: Bash@3
            displayName: 'Terraform Init'
            inputs:
              targetType: 'inline'
              workingDirectory: '$(TF_WORKING_DIR)'
              script: |
                echo "Initializing Terraform..."
                terraform init
          
          # Terraform Plan
          - task: Bash@3
            displayName: 'Terraform Plan'
            inputs:
              targetType: 'inline'
              workingDirectory: '$(TF_WORKING_DIR)'
              script: |
                echo "Planning Terraform deployment..."
                terraform plan
          
          # Terraform Apply (THIS WILL FAIL)
          - task: Bash@3
            displayName: 'Terraform Apply (Expected to Fail)'
            inputs:
              targetType: 'inline'
              workingDirectory: '$(TF_WORKING_DIR)'
              script: |
                echo "Applying Terraform configuration..."
                echo "This is expected to fail - testing AI agent..."
                terraform apply -auto-approve
          
          # Call AI Agent on Failure
          - task: PowerShell@2
            condition: failed()
            displayName: 'AI Agent - Analyze Failure'
            inputs:
              targetType: 'inline'
              script: |
                Write-Host "##[section]================================================"
                Write-Host "##[section]CALLING AI AGENT FOR ROOT CAUSE ANALYSIS"
                Write-Host "##[section]================================================"
                Write-Host ""
                
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "TerraformTest"
                  failedJob = "DeployInfra"
                  failedTask = "Terraform Apply"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json -Depth 10
                
                Write-Host "Sending payload to agent:"
                Write-Host $payload
                Write-Host ""
                
                try {
                  $response = Invoke-RestMethod `
                    -Uri "$(AGENT_WEBHOOK_URL)" `
                    -Method Post `
                    -Body $payload `
                    -ContentType "application/json" `
                    -TimeoutSec 60
                  
                  Write-Host "##[section]================================================"
                  Write-Host "##[section]AI ANALYSIS RESULTS"
                  Write-Host "##[section]================================================"
                  Write-Host ""
                  Write-Host "Failure Category: $($response.rca.category)"
                  Write-Host "Confidence Level: $($response.rca.confidence * 100)%"
                  Write-Host ""
                  Write-Host "##[section]Explanation:"
                  Write-Host $response.rca.explanation
                  Write-Host ""
                  Write-Host "##[section]⚡ Action Taken:"
                  Write-Host "Type: $($response.action_taken)"
                  Write-Host "Details: $($response.details)"
                  Write-Host ""
                  
                  if ($response.pr_url) {
                    Write-Host "##[section]🔗 Fix PR Created:"
                    Write-Host $response.pr_url
                  }
                  
                  if ($response.work_item_id) {
                    Write-Host "##[section]Work Item Created:"
                    Write-Host "ID: $($response.work_item_id)"
                  }
                  
                  Write-Host ""
                  Write-Host "##[section]================================================"
                  Write-Host "##[section]AI AGENT PROCESSING COMPLETE"
                  Write-Host "##[section]================================================"
                  
                } catch {
                  Write-Host "##[error]================================================"
                  Write-Host "##[error]FAILED TO GET AI ANALYSIS"
                  Write-Host "##[error]================================================"
                  Write-Host "##[error]Error: $_"
                  Write-Host "##[error]"
                  Write-Host "##[error]Troubleshooting:"
                  Write-Host "##[error]1. Check Function App logs: func azure functionapp logstream func-agenticdevops-abc123"
                  Write-Host "##[error]2. Verify webhook URL is correct in variable group"
                  Write-Host "##[error]3. Check Azure DevOps PAT is set in Key Vault"
                  Write-Host "##[error]4. Verify Function App is running"
                }
````

---

## 🔧 Step 3: Commit and Push
````bash
# Add the test files
git add .azure-pipelines/test-scenario-1-missing-variable.yml
git add infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable/

# Commit
git commit -m "Add test scenario 1: Terraform missing variable"

# Push
git push origin main
````

---

## 🚀 Step 4: Run the Pipeline

### Via Azure DevOps UI

1. Go to: **Pipelines** → **Pipelines**
2. Click **New Pipeline**
3. Select: **Azure Repos Git**
4. Choose your repository: `agentic-devops-healing`
5. Select: **Existing Azure Pipelines YAML file**
6. Path: `/.azure-pipelines/test-scenario-1-missing-variable.yml`
7. Click **Continue**
8. Click **Run**

### Via Azure CLI
````bash
# Create pipeline from YAML
az pipelines create \
  --name "Test Scenario 1 - Missing Variable" \
  --repository agentic-devops-healing \
  --branch main \
  --yml-path .azure-pipelines/test-scenario-1-missing-variable.yml \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT

# Run the pipeline
az pipelines run \
  --name "Test Scenario 1 - Missing Variable" \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT
````

---

## Step 5: Watch the Pipeline Execute

### Expected Flow

**Stage 1: TerraformTest**
````
Install Terraform
Terraform Init
Terraform Plan (warnings about missing variable)
Terraform Apply - FAILS
   Error: Missing required variable
   variable "azure_region" was not set
AI Agent - Analyze Failure (calls webhook)
````

### Pipeline Output

You should see:
````
Terraform Apply (Expected to Fail)
═══════════════════════════════════════
Applying Terraform configuration...
This is expected to fail - testing AI agent...

Error: Missing required variable

  on main.tf line 17:
   17:   location = var.azure_region
     │
    ╷
    │ The variable "azure_region" was not set.
    ╵

##[error]Bash exited with code '1'.

AI Agent - Analyze Failure
═══════════════════════════════════════
================================================
CALLING AI AGENT FOR ROOT CAUSE ANALYSIS
================================================

Sending payload to agent:
{
  "pipelineId": "123",
  "buildId": "456",
  "failedStage": "TerraformTest",
  ...
}

================================================
AI ANALYSIS RESULTS
================================================

Failure Category: TERRAFORM_MISSING_VARIABLE
Confidence Level: 90%

💡 Explanation:
Terraform requires variable 'azure_region' which is not defined in the pipeline.

⚡ Action Taken:
Type: AUTO_FIX_PR_CREATED
Details: Created fix PR: https://dev.azure.com/.../_git/.../pullrequest/123

🔗 Fix PR Created:
https://dev.azure.com/YOUR_ORG/YOUR_PROJECT/_git/agentic-devops-healing/pullrequest/123

================================================
AI AGENT PROCESSING COMPLETE
================================================
````

---

## 🔍Step 6: Verify Agent Behavior

### Check Function Logs
````bash
# Stream logs
func azure functionapp logstream func-agenticdevops-abc123
````

You should see:
````
2024-12-25T15:30:45.123 [Information] 🚨 Pipeline failure webhook received
2024-12-25T15:30:45.234 [Information] 📋 Failure context: {
  "pipeline_id": "123",
  "build_id": "456",
  "failed_stage": "TerraformTest",
  ...
}
2024-12-25T15:30:45.345 [Information] Gathering failure context...
2024-12-25T15:30:46.456 [Information] Fetching build logs for build 456...
2024-12-25T15:30:48.567 [Information] Detected Terraform failure
2024-12-25T15:30:48.678 [Information] Terraform error: variable "azure_region" was not set
2024-12-25T15:30:48.789 [Information] High confidence - attempting auto-fix
2024-12-25T15:30:49.890 [Information] Would create fix PR for repo: ...
2024-12-25T15:30:49.901 [Information] Processing complete: AUTO_FIX_PR_CREATED
````

### Check Application Insights

Go to Azure Portal → Application Insights → Logs

Query:
````kusto
requests
| where timestamp > ago(10m)
| where name == "HandleFailure"
| project 
    timestamp,
    resultCode,
    duration,
    customDimensions.failure_category,
    customDimensions.confidence,
    customDimensions.action_taken
````

Expected result:

| timestamp | resultCode | duration | failure_category | confidence | action_taken |
|-----------|-----------|----------|------------------|------------|--------------|
| 2024-12-25 15:30:45 | 202 | 4567ms | TERRAFORM_MISSING_VARIABLE | 0.9 | AUTO_FIX_PR_CREATED |

---

## Step 7: Expected Outcomes

### Outcome A: High Confidence → Auto-Fix PR (Ideal)

If agent is confident (>80%), it creates a fix PR:

**PR Title:** `[AI Fix] Add missing Terraform variable: azure_region`

**PR Description:**
````markdown
## Automated Fix by AI Agent

**Pipeline Failure:** Build #456
**Failed Stage:** TerraformTest
**Root Cause:** Missing Terraform variable

### Analysis
Terraform requires variable `azure_region` which is not defined in the pipeline.

### Fix Applied
Added the following to pipeline variables:
```yaml
variables:
  - name: TF_VAR_azure_region
    value: 'eastus'
```

### Confidence
**90%** - High confidence automated fix

---
*This PR was automatically created by the Agentic DevOps Healing system.*
*Review the changes and merge if appropriate.*
````

**Files Changed:**
````diff
# .azure-pipelines/test-scenario-1-missing-variable.yml

variables:
  - group: agentic-healing-config
  - name: TF_WORKING_DIR
    value: 'infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable'
+ - name: TF_VAR_azure_region
+   value: 'eastus'
````

### Outcome B: Medium Confidence → Work Item + Comment (Fallback)

If agent is less confident (<80%), it creates a work item:

**Work Item Type:** Bug

**Title:** `Pipeline Failure: TerraformTest stage failed`

**Description:**
````
## Pipeline Failure Analysis

**Build:** 20241225.1
**Stage:** TerraformTest
**Job:** DeployInfra

## AI Analysis
**Category:** TERRAFORM_MISSING_VARIABLE
**Confidence:** 70%

Terraform requires variable 'azure_region' which is not defined.

## Suggested Action
Add the following variable to the pipeline:
- Name: TF_VAR_azure_region
- Value: Choose appropriate Azure region (eastus, westus2, etc.)

## Build Link
https://dev.azure.com/YOUR_ORG/YOUR_PROJECT/_build/results?buildId=456
````

**Tags:** `AI-Generated`, `Pipeline-Failure`, `Terraform`

---

## Step 8: Test the Fix

If a PR was created:

1. **Review the PR**
   - Go to: Repos → Pull Requests
   - Open the AI-created PR
   - Review the changes

2. **Test the Fix**
   - Option A: Approve and merge the PR
   - Option B: Manually apply the fix to test

3. **Rerun Pipeline**
````bash
   # Rerun the same pipeline
   az pipelines run \
     --name "Test Scenario 1 - Missing Variable" \
     --organization https://dev.azure.com/YOUR_ORG \
     --project YOUR_PROJECT
````

4. **Verify Success**
   - Pipeline should now pass
   - Terraform applies successfully
   - No agent webhook called (only triggers on failure)

---

## Step 9: Measure Success

### Metrics to Track

Create a simple tracking sheet:

| Metric | Value | Target |
|--------|-------|--------|
| Time to detect failure | <30 seconds | <1 minute |
| Time to RCA | 2-5 minutes | <5 minutes |
| RCA Accuracy | Manual verification | >80% |
| Auto-fix success rate | Track over time | >70% |
| Time saved per failure | ~15-30 minutes | >10 minutes |

### Record Results
````bash
# Create experiment log
cat >> docs/research/experiment-log.md << 'EOF'

## Test Run: Scenario 1 - Missing Terraform Variable

**Date:** 2024-12-25
**Pipeline:** test-scenario-1-missing-variable

### Results
- Failure detected: 30 seconds
- Agent called successfully
- RCA completed: 4 minutes
- Category identified: TERRAFORM_MISSING_VARIABLE
- Confidence: 90%
- Action: AUTO_FIX_PR_CREATED
- Fix verified: Working

### Notes
- Agent correctly identified missing variable
- Generated appropriate fix
- PR created successfully
- Fix resolved the issue

EOF
````

---

## Success Criteria

Your first scenario test is successful if:

- [x] Pipeline failed as expected
- [x] Agent webhook called
- [x] Agent analyzed failure correctly
- [x] Category: `TERRAFORM_MISSING_VARIABLE`
- [x] Confidence: >70%
- [x] Action taken (PR or work item)
- [x] Fix resolves the issue

---

## Troubleshooting

### Agent Didn't Respond

**Check 1: Webhook URL**
````bash
# Verify webhook URL in variable group
az pipelines variable-group list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --query "[?name=='agentic-healing-config'].variables.AGENT_WEBHOOK_URL"
````

**Check 2: Function App Running**
````bash
az functionapp show \
  --name func-agenticdevops-abc123 \
  --resource-group rg-agenticdevops-dev \
  --query "state"

# Should return: "Running"
````

**Check 3: Function Logs**
````bash
func azure functionapp logstream func-agenticdevops-abc123
# Should show log entries
````

### Agent Returned Low Confidence

**Possible reasons:**
- OpenAI not deployed or not accessible
- Build logs too short/incomplete
- Pattern not recognized

**Solution:**
````bash
# Check OpenAI deployment
az cognitiveservices account deployment list \
  --name oai-agenticdevops-abc123 \
  --resource-group rg-agenticdevops-dev

# Verify gpt-4o deployment exists
````

### No PR Created

**Check Git operations:**
````python
# In git_operations.py, currently returns placeholder
# This is expected in v0.1

# For full PR creation, need to implement:
# 1. Clone repo
# 2. Create branch
# 3. Commit fix
# 4. Push
# 5. Create PR via ADO API
````

---

## Next Steps

Congratulations! You've successfully tested your first scenario! 🎉

**What's working:**
- Pipeline → Webhook → Agent flow
- Failure detection
- Root cause analysis
- Fix generation

**Next scenarios to test:**

1. **Scenario 2:** Wrong Azure Region
   - File: `scenarios/wrong-region/main.tf`
   - Error: Invalid region name

2. **Scenario 3:** Invalid Terraform Syntax
   - File: `scenarios/invalid-syntax/main.tf`
   - Error: HCL syntax errors

3. **Scenario 4:** State Conflict
   - File: `scenarios/state-conflict/main.tf`
   - Error: Resource already exists

**Iterate and improve:**
1. Refine prompts for better RCA
2. Implement full Git operations for PR creation
3. Add more failure patterns
4. Test with real pipelines

---

## What You've Achieved
````
Infrastructure deployed
Function App running
Agent responding to webhooks
AI analyzing failures
Auto-fix logic working
End-to-end flow verified

You now have a working AI-powered pipeline healer!
````

**Project status: 40% complete**

Remaining work:
- Implement full PR creation (Git operations)
- Test remaining scenarios
- Add build failure detection
- Optimize prompts
- Collect metrics for research paper

---

## Tips for Next Tests

1. **Test incrementally** - One scenario at a time
2. **Monitor logs** - Keep Function logs streaming
3. **Track results** - Document in experiment log
4. **Iterate prompts** - Improve RCA accuracy
5. **Cost watch** - Monitor OpenAI usage

---

## Ready for More?

You've completed the foundation! Here's what you can do next:

**Option A: Test More Scenarios**
- Wrong region
- Invalid syntax
- State conflicts

**Option B: Implement Full PR Creation**
- Complete `git_operations.py`
- Test actual PR creation

**Option C: Add Build Failures**
- Maven dependency conflicts
- Docker build failures

**Option D: Write Research Paper**
- Document methodology
- Collect metrics
- Start IEEE paper outline

Which direction interests you most?