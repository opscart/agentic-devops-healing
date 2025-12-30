# Agentic DevOps Healing

AI-assisted pipeline remediation system that automatically detects, analyzes, and generates code fixes for Azure DevOps pipeline failures.

## Overview

This system reduces mean time to resolution (MTTR) from 30 minutes to under 2 minutes by automating failure investigation and code generation, while maintaining human review for all changes.

**Key Features:**
- Automatic failure detection via Azure DevOps webhooks
- AI-powered root cause analysis using GPT-5.2
- Actual code generation (not just suggestions)
- GitHub pull request creation with executable fixes
- Intelligent decision-making based on confidence scores
- Human-in-the-loop design (all fixes require review)

**Results:**
- 95%+ detection accuracy across test scenarios
- 93% time reduction (30 min → 2 min)
- Production-ready code generation
- Safe handling of syntax errors (never auto-fixed)

## Architecture

```
Pipeline Failure → Azure Function → Analysis Engine → Decision Logic → GitHub PR → Human Review → Merge
```

**Components:**
1. **Azure Function** - Webhook receiver and orchestrator
2. **Pattern Detection** - Fast local analysis (95%+ confidence)
3. **AI Analysis** - GPT-5.2 for complex failures
4. **Code Generator** - Language-specific fix generation
5. **GitHub Integration** - PR creation and management

**Decision Logic:**
- Confidence ≥80% + Safe → Generate code and create PR
- Confidence 65-80% OR Unsafe → Create PR with suggestions
- Confidence <65% → Create work item for investigation

## Setup

### Prerequisites

- Python 3.11+
- Azure Functions Core Tools 4.x
- Azure DevOps account with pipelines
- GitHub account and personal access token
- OpenAI API key (GPT-5.2 access)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/opscart/agentic-devops-healing.git
cd agentic-devops-healing
```

2. Create Python virtual environment:
```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
cd src/agents/infra-healer
pip install -r requirements.txt --break-system-packages
```

4. Configure environment variables:
```bash
cp local.settings.json.example local.settings.json
```

Edit `local.settings.json` with your credentials:
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "OPENAI_API_KEY": "your-openai-api-key",
    "OPENAI_DEPLOYMENT_NAME": "gpt-5.2",
    "ADO_ORGANIZATION_URL": "https://dev.azure.com/yourorg",
    "ADO_PROJECT_NAME": "your-project",
    "ADO_PAT": "your-azure-devops-pat",
    "GITHUB_TOKEN": "your-github-token",
    "GITHUB_REPO_OWNER": "your-github-username",
    "GITHUB_REPO_NAME": "your-repo-name"
  }
}
```

### Running Locally

Navigate to the function directory and start:

```bash
cd ~/Source/agentic-devops-healing/src/agents/infra-healer

# Verify you're in the right directory
pwd
# Should output: /Users/username/Source/agentic-devops-healing/src/agents/infra-healer

# Check directory contents
ls -l
# Should show: function_app.py, analyzers/, fixers/, handlers/, etc.

# Start the Azure Function
func start
```

**Expected output:**
```
Azure Functions Core Tools
Core Tools Version:       4.6.0
Function Runtime Version: 4.1045.200.25556

Functions:
    HandleFailure: [POST] http://localhost:7071/api/HandleFailure

For detailed output, run func with --verbose flag.
```

The function is now listening on `http://localhost:7071/api/HandleFailure`

## Usage

### Manual Testing

Trigger the function manually with a pipeline failure:

```bash
curl -X POST http://localhost:7071/api/HandleFailure \
  -H "Content-Type: application/json" \
  -d '{
    "pipelineId": "23",
    "buildId": "575",
    "projectName": "AI-DevOps-POC"
  }'
```

**Response (within 15 seconds):**
```json
{
  "status": "success",
  "rca": {
    "category": "TERRAFORM_MISSING_VARIABLE",
    "confidence": 0.95,
    "explanation": "Variable 'azure_region' not defined in variables.tf"
  },
  "action_taken": "AUTO_FIX_PR_CREATED",
  "pr_url": "https://github.com/your-repo/pull/28"
}
```

### Production Deployment

1. Deploy to Azure Functions:
```bash
func azure functionapp publish <your-function-app-name>
```

2. Configure Azure DevOps webhook:
   - Go to Project Settings → Service Hooks
   - Create new webhook for "Build completed" events
   - Filter: Status = Failed
   - URL: `https://<your-function-app>.azurewebsites.net/api/HandleFailure`

3. The system will now automatically respond to pipeline failures

## Test Scenarios

Three test scenarios demonstrate the system's capabilities:

### Scenario 1: Missing Terraform Variable

**Error:**
```
Error: Reference to undeclared input variable
  on main.tf line 18:
  18:   location = var.azure_region
```

**Result:**
- Detection: 100% accurate
- Confidence: 95%
- Action: Generated code and created PR
- PR: [#28](https://github.com/opscart/agentic-devops-healing/pull/28)
- Generated fix:
```hcl
variable "azure_region" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "eastus"
}
```

### Scenario 2: Invalid Azure Region

**Error:**
```
Error: "east-us" was not found in the list of supported Azure Locations
  on main.tf line 18:
  18:   location = "east-us"
```

**Result:**
- Detection: 100% accurate
- Confidence: 99%
- Action: Fetched file from GitHub, fixed region, created PR
- PR: [#32](https://github.com/opscart/agentic-devops-healing/pull/32)
- Generated fix:
```diff
- location = "east-us"
+ location = "eastus"
```

### Scenario 3: Terraform Syntax Error

**Error:**
```
Error: Missing closing brace in interpolation
  on main.tf line 25:
  25:   name = "rg-${var.prefix-${var.environment}"
```

**Result:**
- Detection: 100% accurate
- Confidence: 98%
- Action: Created PR with fix suggestions (no code generation)
- PR: [#33](https://github.com/opscart/agentic-devops-healing/pull/33)
- Reasoning: Syntax errors require human review for safety

## Project Structure

```
agentic-devops-healing/
├── src/
│   ├── agents/
│   │   └── infra-healer/          # Main Azure Function
│   │       ├── analyzers/          # Failure pattern detection
│   │       │   ├── terraform_analyzer.py
│   │       │   └── pipeline_analyzer.py
│   │       ├── function_app.py     # Entry point (22KB)
│   │       ├── requirements.txt    # Python dependencies
│   │       └── local.settings.json # Configuration
│   └── shared/
│       ├── ado_client.py           # Azure DevOps integration
│       ├── code_generator.py       # Code generation engine
│       ├── github_operations.py    # GitHub PR management
│       └── openai_client.py        # AI analysis client
├── infrastructure/
│   ├── core/                       # Production infrastructure
│   └── test-apps/                  # Test scenarios
│       └── infra-only/terraform/scenarios/
│           ├── missing-variable/   # Scenario 1
│           ├── wrong-region/       # Scenario 2
│           └── invalid-syntax/     # Scenario 3
└── .azure-pipelines/               # Test pipeline definitions
```

## How It Works

### 1. Detection (< 1 second)
Pipeline fails → Azure DevOps webhook → Azure Function triggered

### 2. Context Gathering (3-5 seconds)
- Fetch build logs from failed pipeline
- Fetch last successful build for comparison
- Fetch pipeline YAML definition

### 3. Analysis (5-10 seconds)
- **Pattern Detection:** Check for known failure patterns (95%+ confidence)
- **AI Analysis:** Use GPT-5.2 for complex/novel failures
- **Override Logic:** If pattern confidence ≥90%, override AI classification

### 4. Decision Making (< 1 second)
```
IF confidence ≥ 80% AND safe to auto-fix:
    → Generate code and create PR
ELIF confidence ≥ 65% OR unsafe (syntax errors):
    → Create PR with suggestions only
ELSE:
    → Create work item for human investigation
```

### 5. Code Generation (2-3 seconds, if applicable)
- Extract context from build logs (no hardcoding)
- Generate language-specific fixes
- For file modifications: Fetch from GitHub, modify, return

### 6. PR Creation (2-3 seconds)
- Create feature branch
- Commit changes (code or suggestion document)
- Open pull request with detailed description
- Add labels: `ai-generated`, `automated`
- Check for duplicates (prevent redundant PRs)

### 7. Human Review (1-2 minutes)
**Critical:** All fixes require human approval
- Developer reviews AI-generated code
- Approves if correct, or modifies if needed
- Merges when satisfied

### 8. Validation (automatic)
Pipeline re-runs after merge → Should now succeed

## Performance Metrics

| Metric | Traditional | AI-Assisted | Improvement |
|--------|-------------|-------------|-------------|
| Detection Time | Manual | < 1 second | Instant |
| Investigation | 15 minutes | 10 seconds | 99% faster |
| Coding Fix | 10 minutes | 3 seconds | 99% faster |
| Human Review | N/A | 1-2 minutes | New step |
| Total MTTR | 30 minutes | 2 minutes | 93% faster |

**Time Breakdown (AI-Assisted):**
- Automated (detection + analysis + code gen): 15 seconds
- Human (review + approve): 1-2 minutes
- Total: ~2 minutes

## Safety Features

1. **Human-in-the-Loop:** All changes require human approval
2. **Syntax Errors Never Auto-Fixed:** Even at 98% confidence
3. **Tiered Confidence Model:** Different actions based on risk
4. **Duplicate Prevention:** Won't create redundant PRs
5. **Git History:** Full audit trail of AI generation + human approval

## Configuration

### Confidence Thresholds

Adjust in `src/agents/infra-healer/function_app.py`:

```python
# High confidence threshold (auto-generate code)
HIGH_CONFIDENCE = 0.80

# Medium confidence threshold (suggestions only)
MEDIUM_CONFIDENCE = 0.65
```

### Pattern Detection

Add new patterns in `src/agents/infra-healer/analyzers/terraform_analyzer.py`:

```python
def detect_error_pattern(build_logs: str) -> tuple:
    if 'your new pattern' in build_logs:
        return ('YOUR_CATEGORY', 0.95)
```

### Code Generators

Add new generators in `src/shared/code_generator.py`:

```python
def generate_your_fix(explanation: str, context: dict) -> dict:
    # Your code generation logic
    return {filepath: generated_code}
```

## Limitations

1. **Terraform-Specific:** Currently handles only Terraform failures
2. **Single-File Changes:** Best for single-file modifications
3. **No Rollback:** Manual intervention required if fix breaks something
4. **API Rate Limits:** OpenAI API calls are rate-limited

## Future Enhancements

- Multi-language support (Python, Docker, Kubernetes)
- Multi-file code generation
- Automatic rollback on failure
- Learning from merged vs. closed PRs
- Cost optimization (cache AI responses)

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Author

**Shamsher Khan**
- Senior DevOps Engineer at GlobalLogic (Hitachi)
- IEEE Senior Member
- DZone Contributor


## Acknowledgments

- Azure Functions for serverless hosting
- OpenAI GPT-5.2 for AI analysis
- Python 3.11 and PyGithub library
- Azure DevOps for pipeline automation

## References

- [Publication Article](docs/article.md)
- [Test Scenarios](infrastructure/test-apps/infra-only/terraform/scenarios/)
- [Example PRs](https://github.com/opscart/agentic-devops-healing/pulls?q=is%3Apr+label%3Aai-generated)