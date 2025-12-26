# Configure Azure DevOps Pipeline

This guide shows how to add the AI agent webhook to your Azure DevOps pipelines.

---

## Overview

We need to configure your Azure DevOps pipeline to:
1. Call the agent webhook when a stage fails
2. Pass failure context (build ID, stage name, etc.)
3. Allow the agent to access build logs and create PRs

---

## Prerequisites

Before starting, you need:

- Agent infrastructure deployed (from previous step)
- Function App webhook URL
- Function key
- Azure DevOps PAT set in Key Vault

### Get Your Webhook URL
````bash
cd infrastructure/core/terraform

# Get webhook URL
terraform output -raw webhook_url

# Example output:
# https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure
````

### Get Your Function Key
````bash
# Get function key
func azure functionapp list-functions func-agenticdevops-abc123 --show-keys

# Look for:
# Function Keys:
#   default: xyz123abc456def789...
````

**Complete webhook URL:**
````
https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=xyz123abc456def789...
````

---

## Step 1: Create Pipeline Variable

We'll store the webhook URL as a pipeline variable for reusability.

### Option A: Via Azure DevOps UI

1. Go to your Azure DevOps project
2. Navigate to: **Pipelines** → **Library**
3. Click **+ Variable group**
4. Name: `agentic-healing-config`
5. Add variable:
   - Name: `AGENT_WEBHOOK_URL`
   - Value: `https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=xyz123...`
   - Keep value secret: **Yes**
6. Click **Save**

### Option B: Via Azure CLI
````bash
# Set as pipeline variable
az pipelines variable create \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --pipeline-name YOUR_PIPELINE_NAME \
  --name AGENT_WEBHOOK_URL \
  --value "https://func-agenticdevops-abc123.azurewebsites.net/api/HandleFailure?code=xyz123..." \
  --secret true
````

---

## Step 2: Add Webhook to Pipeline YAML

There are **two approaches** to integrate the agent:

### Approach A: Individual Stage Handlers (Recommended)

Add a failure handler to **each critical stage**:
````yaml
# azure-pipelines.yml

trigger:
  - main
  - develop

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentic-healing-config  # Variable group from Step 1

stages:
  - stage: Build
    jobs:
      - job: BuildJob
        steps:
          - task: Maven@3
            displayName: 'Maven Build'
            inputs:
              mavenPomFile: 'pom.xml'
              goals: 'clean package'
          
          # AGENT WEBHOOK - Triggers on failure
          - task: PowerShell@2
            condition: failed()  # Only runs if previous steps failed
            displayName: 'Notify AI Agent on Failure'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "$(System.StageName)"
                  failedJob = "$(System.JobName)"
                  failedTask = "Maven@3"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                
                Write-Host "Calling AI agent..."
                Write-Host "Payload: $payload"
                
                try {
                  $response = Invoke-RestMethod `
                    -Uri "$(AGENT_WEBHOOK_URL)" `
                    -Method Post `
                    -Body $payload `
                    -ContentType "application/json"
                  
                  Write-Host "Agent response:"
                  Write-Host ($response | ConvertTo-Json -Depth 10)
                } catch {
                  Write-Host "Failed to call agent: $_"
                  # Don't fail the pipeline if webhook fails
                }

  - stage: Infrastructure
    dependsOn: Build
    jobs:
      - job: TerraformJob
        steps:
          - task: TerraformCLI@0
            displayName: 'Terraform Apply'
            inputs:
              command: 'apply'
              workingDirectory: 'terraform'
              environmentServiceName: 'AzureServiceConnection'
          
          # AGENT WEBHOOK - For Terraform failures
          - task: PowerShell@2
            condition: failed()
            displayName: 'Notify AI Agent on Terraform Failure'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "Infrastructure"
                  failedJob = "TerraformJob"
                  failedTask = "TerraformCLI@0"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                
                Write-Host "Calling AI agent for Terraform failure..."
                
                try {
                  $response = Invoke-RestMethod `
                    -Uri "$(AGENT_WEBHOOK_URL)" `
                    -Method Post `
                    -Body $payload `
                    -ContentType "application/json"
                  
                  Write-Host "Agent response:"
                  Write-Host ($response | ConvertTo-Json -Depth 10)
                  
                  # Check if agent created a fix PR
                  if ($response.action_taken -eq "AUTO_FIX_PR_CREATED") {
                    Write-Host "##[section]🤖 AI Agent created a fix PR!"
                    Write-Host "##[section]📝 Check: $($response.details)"
                  }
                } catch {
                  Write-Host "##[warning]Failed to call agent: $_"
                }

  - stage: Deploy
    dependsOn: Infrastructure
    jobs:
      - job: DeployJob
        steps:
          - task: AzureWebApp@1
            displayName: 'Deploy to Azure'
            inputs:
              azureSubscription: 'AzureServiceConnection'
              appName: 'my-app'
              package: '$(Build.ArtifactStagingDirectory)/**/*.zip'
          
          # AGENT WEBHOOK - For deployment failures
          - task: PowerShell@2
            condition: failed()
            displayName: 'Notify AI Agent on Deploy Failure'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "Deploy"
                  failedJob = "DeployJob"
                  failedTask = "AzureWebApp@1"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                
                Invoke-RestMethod `
                  -Uri "$(AGENT_WEBHOOK_URL)" `
                  -Method Post `
                  -Body $payload `
                  -ContentType "application/json" `
                  -ErrorAction SilentlyContinue
````

### Approach B: Global Pipeline Failure Handler (Simpler)

Add a **single handler** at the end that catches all failures:
````yaml
# azure-pipelines.yml

trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentic-healing-config

stages:
  - stage: Build
    jobs:
      - job: BuildJob
        steps:
          - task: Maven@3
            inputs:
              mavenPomFile: 'pom.xml'
              goals: 'clean package'

  - stage: Infrastructure
    jobs:
      - job: TerraformJob
        steps:
          - task: TerraformCLI@0
            inputs:
              command: 'apply'
              workingDirectory: 'terraform'

  # GLOBAL FAILURE HANDLER - Runs if ANY stage fails
  - stage: NotifyAgent
    condition: failed()  # Only runs if any previous stage failed
    jobs:
      - job: CallAgent
        steps:
          - task: PowerShell@2
            displayName: 'Call AI Agent'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "Unknown"  # Agent will determine from logs
                  failedJob = "Unknown"
                  failedTask = "Unknown"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                
                Invoke-RestMethod `
                  -Uri "$(AGENT_WEBHOOK_URL)" `
                  -Method Post `
                  -Body $payload `
                  -ContentType "application/json"
````

---

## 🔧 Step 3: Test the Integration

### Create a Test Pipeline

Create a simple test pipeline that deliberately fails:
````yaml
# test-agent-pipeline.yml

trigger: none  # Manual trigger only

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentic-healing-config

stages:
  - stage: TestFailure
    jobs:
      - job: FailJob
        steps:
          # This will fail
          - bash: |
              echo "Simulating a pipeline failure..."
              exit 1
            displayName: 'Deliberate Failure'
          
          # Agent webhook
          - task: PowerShell@2
            condition: failed()
            displayName: 'Call AI Agent'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  failedStage = "TestFailure"
                  failedJob = "FailJob"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                } | ConvertTo-Json
                
                Write-Host "Calling agent..."
                $response = Invoke-RestMethod `
                  -Uri "$(AGENT_WEBHOOK_URL)" `
                  -Method Post `
                  -Body $payload `
                  -ContentType "application/json"
                
                Write-Host "Response:"
                Write-Host ($response | ConvertTo-Json -Depth 10)
````

### Run the Test

1. Commit `test-agent-pipeline.yml` to your repo
2. In Azure DevOps: **Pipelines** → **New Pipeline**
3. Select your repo
4. Choose **Existing Azure Pipelines YAML file**
5. Select `test-agent-pipeline.yml`
6. Click **Run**

### Verify Agent Response

In the pipeline logs, you should see:
````
Calling agent...
Payload: {
  "pipelineId": "123",
  "buildId": "456",
  ...
}

Response:
{
  "status": "success",
  "failure_context": {...},
  "rca": {
    "category": "UNKNOWN_ERROR",
    "confidence": 0.3,
    "explanation": "Build failed but specific error type not recognized..."
  },
  "action_taken": "WORK_ITEM_CREATED",
  "details": "Created work item: 789"
}
````

---

## Step 4: Monitor Agent Activity

### View Function Logs
````bash
# Stream live logs from Function App
func azure functionapp logstream func-agenticdevops-abc123

# You'll see:
# 2024-12-25T10:30:15.123 [Information] Pipeline failure webhook received
# 2024-12-25T10:30:15.234 [Information] Failure context: {...}
# 2024-12-25T10:30:16.345 [Information] Gathering failure context...
# 2024-12-25T10:30:18.456 [Information] Analyzing failure with OpenAI...
# 2024-12-25T10:30:22.567 [Information] Executing remediation...
# 2024-12-25T10:30:24.678 [Information] Processing complete: WORK_ITEM_CREATED
````

### View in Application Insights
````bash
# Open in Azure Portal
echo "https://portal.azure.com/#@/resource/subscriptions/YOUR_SUB/resourceGroups/rg-agenticdevops-dev/providers/microsoft.insights/components/appi-agenticdevops-dev/logs"
````

Query recent requests:
````kusto
requests
| where timestamp > ago(1h)
| where name == "HandleFailure"
| project timestamp, resultCode, duration, customDimensions
| order by timestamp desc
````

### Check Azure DevOps Work Items

If the agent created a work item:

1. Go to **Azure Boards** → **Work Items**
2. Filter by: Tags contains `AI-Generated`
3. You should see bug created by the agent

---

## Step 5: Real Scenario - Terraform Failure

Now let's test with an actual Terraform failure (our first scenario).

### Create Test Infrastructure Pipeline
````yaml
# infrastructure-test-pipeline.yml

trigger: none

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentic-healing-config

stages:
  - stage: TerraformDeploy
    jobs:
      - job: ApplyInfra
        steps:
          # Install Terraform
          - task: TerraformInstaller@0
            inputs:
              terraformVersion: 'latest'
          
          # Initialize
          - task: TerraformCLI@0
            displayName: 'Terraform Init'
            inputs:
              command: 'init'
              workingDirectory: '$(System.DefaultWorkingDirectory)/infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable'
          
          # Apply (this will fail - missing variable)
          - task: TerraformCLI@0
            displayName: 'Terraform Apply'
            inputs:
              command: 'apply'
              workingDirectory: '$(System.DefaultWorkingDirectory)/infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable'
              commandOptions: '-auto-approve'
          
          # Call agent on failure
          - task: PowerShell@2
            condition: failed()
            displayName: 'AI Agent - Analyze Terraform Failure'
            inputs:
              targetType: 'inline'
              script: |
                $payload = @{
                  pipelineId = "$(System.DefinitionId)"
                  buildId = "$(Build.BuildId)"
                  buildNumber = "$(Build.BuildNumber)"
                  prId = "$(System.PullRequest.PullRequestId)"
                  failedStage = "TerraformDeploy"
                  failedJob = "ApplyInfra"
                  failedTask = "TerraformCLI@0"
                  repoUrl = "$(Build.Repository.Uri)"
                  sourceBranch = "$(Build.SourceBranch)"
                  projectName = "$(System.TeamProject)"
                  organizationUrl = "$(System.CollectionUri)"
                  timestamp = (Get-Date).ToUniversalTime().ToString("o")
                } | ConvertTo-Json
                
                Write-Host "##[section]Calling AI Agent for Terraform failure analysis..."
                
                try {
                  $response = Invoke-RestMethod `
                    -Uri "$(AGENT_WEBHOOK_URL)" `
                    -Method Post `
                    -Body $payload `
                    -ContentType "application/json" `
                    -TimeoutSec 30
                  
                  Write-Host "##[section]AI Analysis Results:"
                  Write-Host "Category: $($response.rca.category)"
                  Write-Host "Confidence: $($response.rca.confidence)"
                  Write-Host "Explanation: $($response.rca.explanation)"
                  Write-Host ""
                  Write-Host "##[section]⚡ Action Taken: $($response.action_taken)"
                  Write-Host "Details: $($response.details)"
                  
                  if ($response.pr_url) {
                    Write-Host "##[section]🔗 Fix PR: $($response.pr_url)"
                  }
                } catch {
                  Write-Host "##[error]Failed to get AI analysis: $_"
                }
````

### Expected Agent Behavior

When this pipeline runs and fails:

1. Agent receives webhook
2. Fetches build logs
3. Detects: "Missing required variable"
4. Analyzes with AI or pattern matching
5. Determines: `TERRAFORM_MISSING_VARIABLE`
6. Confidence: `0.9` (HIGH)
7. Generates fix YAML
8. Creates PR or posts comment

---

## 🛠️ Troubleshooting

### Issue: Webhook Not Called

**Check:**
````yaml
# Ensure condition is correct
condition: failed()  # Correct

# NOT:
condition: always()  # Runs even on success
````

**Verify variable group:**
````bash
# Check if variable exists
az pipelines variable-group list \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT \
  --query "[?name=='agentic-healing-config']"
````

### Issue: 401 Unauthorized

**Problem:** Function key is wrong or missing

**Solution:**
````bash
# Get fresh function key
func azure functionapp list-functions func-agenticdevops-abc123 --show-keys

# Update variable group with new URL including key
````

### Issue: Agent Returns Error

**Check Function logs:**
````bash
func azure functionapp logstream func-agenticdevops-abc123
````

**Common errors:**
- `ADO_PAT not set` → Set PAT in Key Vault
- `Missing required fields` → Check payload structure
- `OpenAI API error` → Verify OpenAI deployment exists

### Issue: Agent Times Out

**Increase webhook timeout:**
````yaml
- task: PowerShell@2
  inputs:
    script: |
      Invoke-RestMethod `
        -Uri "$(AGENT_WEBHOOK_URL)" `
        -Method Post `
        -Body $payload `
        -ContentType "application/json" `
        -TimeoutSec 60  # Increase from default 30
````

---

## Configuration Checklist

Before proceeding to testing:

- [ ] Webhook URL stored in variable group
- [ ] Variable group linked to pipeline
- [ ] Failure handler added to pipeline YAML
- [ ] Test pipeline created and run successfully
- [ ] Agent responded to test webhook
- [ ] Function logs show agent processing
- [ ] Application Insights showing telemetry

---

## Next Steps

Pipeline is now configured!

**Next:** Test with real failure scenarios

👉 See: `docs/setup/04-test-first-scenario.md`

---

## 💡 Best Practices

### 1. Selective Agent Activation

Don't call the agent for every failure. Target specific scenarios:
````yaml
# Only for infrastructure stages
- stage: Infrastructure
  jobs:
    - job: Terraform
      steps:
        - task: TerraformCLI@0
          # ...
        
        - task: PowerShell@2
          condition: failed()  # Call agent
````

### 2. Pipeline Performance

Agent calls are async and don't block:
````yaml
# Agent call doesn't fail the pipeline
- task: PowerShell@2
  condition: failed()
  continueOnError: true  # Don't fail if webhook fails
  inputs:
    script: |
      Invoke-RestMethod ... -ErrorAction SilentlyContinue
````

### 3. Security

Never log the function key:
````yaml
# DON'T DO THIS
Write-Host "Calling $(AGENT_WEBHOOK_URL)"

# DO THIS
Write-Host "Calling AI agent..."
````

### 4. Rate Limiting

For high-frequency pipelines, add cooldown:
````yaml
# Only call agent if last call was >5 minutes ago
- bash: |
    LAST_CALL=$(az storage blob download ...)
    CURRENT_TIME=$(date +%s)
    if [ $((CURRENT_TIME - LAST_CALL)) -gt 300 ]; then
      # Call webhook
    fi
````

---

## 🎉 You're All Set!

Your Azure DevOps pipelines will now automatically:
1. Detect failures
2. Call AI agent
3. Get root cause analysis
4. Receive auto-fixes (for infrastructure issues)
5. Create work items (for complex issues)

Ready to test!