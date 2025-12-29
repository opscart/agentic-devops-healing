# Agentic DevOps Healing

An AI-powered autonomous pipeline remediation system that detects, analyzes, and creates fix proposals for CI/CD failures.

**Status:** Research Prototype | **Phase:** Local Development & Testing | **Last Updated:** December 2025

## Overview

This research project explores autonomous remediation of DevOps pipeline failures using Large Language Models. The system analyzes Azure DevOps pipeline failures, performs root cause analysis with GPT-5.2, and automatically creates GitHub pull requests with detailed fix suggestions.

**Current Implementation:**
- AI-powered failure detection and analysis
- GitHub PR creation with fix recommendations
- Intelligent auto-fix vs manual review decisions
- Multi-platform integration (Azure DevOps + GitHub)

**Testing Results:**
- Detection accuracy: 100% (5/5 scenarios)
- Root cause analysis accuracy: 100% (5/5 scenarios)
- Response time: 3-5 seconds average
- Auto-fix decision accuracy: 100% (5/5 correct)

## Architecture
```
Azure DevOps Pipeline Failure
        ↓
AI Agent (Python + GPT-5.2)
    ├── Fetch build logs via Azure DevOps API
    ├── Analyze with GPT-5.2
    ├── Classify error type
    └── Determine remediation strategy
        ↓
Decision Engine
    ├── High confidence + auto-fixable → GitHub PR
    └── Low confidence or syntax error → Work Item
        ↓
GitHub Pull Request
    ├── Detailed root cause analysis
    ├── Step-by-step fix instructions
    ├── Code snippets
    └── Triggers CI/CD validation
        ↓
Developer Review & Merge
```

## Current Capabilities

**Supported Failure Types:**
- Missing Terraform variables
- Invalid Azure region formats
- Terraform syntax errors
- Configuration errors

**Integration:**
- Azure DevOps (build logs, work items)
- GitHub (PR creation, branch management)
- OpenAI GPT-5.2 (analysis)

**Safety Features:**
- Duplicate PR prevention
- Syntax errors always escalate to human review
- All PRs require human approval before merge
- Confidence-based decision making

## Technology Stack

- **Language:** Python 3.11
- **AI Model:** OpenAI GPT-5.2
- **Platform:** Azure Functions (local development)
- **Integration:** Azure DevOps Python API, PyGithub
- **Infrastructure:** Terraform (for future Azure deployment)

## Quick Start

### Prerequisites

- Python 3.11+
- Azure DevOps organization with pipelines
- GitHub repository
- OpenAI API key
- Azure Functions Core Tools

### Local Setup

1. Clone repository
```bash
git clone https://github.com/opscart/agentic-devops-healing.git
cd agentic-devops-healing
```

2. Install dependencies
```bash
cd src/agents/infra-healer
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

3. Configure environment
```bash
cp local.settings.json.example local.settings.json
# Edit local.settings.json with your credentials:
# - OPENAI_API_KEY (from openai.com)
# - ADO_PAT (Azure DevOps Personal Access Token)
# - GITHUB_TOKEN (GitHub Personal Access Token)
```

4. Run locally
```bash
func start
```

5. Test with a pipeline failure
```bash
curl -X POST http://localhost:7071/api/HandleFailure \
  -H "Content-Type: application/json" \
  -d '{
    "pipelineId": "YOUR_PIPELINE_ID",
    "buildId": "YOUR_BUILD_ID",
    "projectName": "YOUR_PROJECT"
  }'
```

See [docs/setup/](docs/setup/) for detailed setup instructions.

## Repository Structure
```
agentic-devops-healing/
├── infrastructure/
│   ├── core/                      # Terraform for Azure deployment (future)
│   └── test-apps/                 # Test scenarios
├── src/
│   ├── agents/
│   │   └── infra-healer/         # Main agent implementation
│   │       ├── analyzers/        # Failure analysis logic
│   │       ├── function_app.py   # Azure Functions entry point
│   │       └── requirements.txt  # Python dependencies
│   └── shared/                    # Common libraries
│       ├── ado_client.py         # Azure DevOps integration
│       ├── github_operations.py  # GitHub PR automation
│       └── openai_client.py      # OpenAI API wrapper
├── .azure-pipelines/              # Test pipeline scenarios
└── docs/                          # Documentation
```

## Test Scenarios

Four deliberate failure scenarios for testing:

1. **Missing Variable** - Terraform references undefined variable
2. **Wrong Region** - Invalid Azure region format ("east-us" vs "eastus")
3. **Syntax Error** - Missing closing brace in Terraform
4. **Simple Failure** - Generic failure for testing

Run scenarios:
```bash
az pipelines run --name test-scenario-1-missing-variable \
  --organization https://dev.azure.com/YOUR_ORG \
  --project YOUR_PROJECT
```

## Limitations and Future Work

**Current Limitations:**
- PRs contain fix suggestions, not actual code changes
- Confidence scores are AI self-assessed (not statistically validated)
- Small test set (5 scenarios)
- Local deployment only (Azure deployment pending quota approval)

**Planned Enhancements:**
- Code generation for common patterns
- Multi-model ensemble for confidence validation
- Support for Java/Maven, Docker build failures
- Historical success rate tracking
- Confidence calibration based on merge outcomes
- Azure deployment with webhooks

## Research

This project serves as the foundation for academic research on AI-assisted DevOps automation:

**Publications:**
- InfoQ Article: In progress
- IEEE Conference Paper: In progress

**Research Questions:**
- Can LLMs accurately diagnose infrastructure failures?
- What confidence thresholds balance automation with safety?
- How to validate AI-generated fixes before deployment?

See [docs/research/](docs/research/) for experiment logs and methodology.

## Development Cost

**Current (Local Development):**
- OpenAI API: $2-5/month (testing usage)
- Azure DevOps: Free tier
- GitHub: Free tier

**Future (Azure Deployment):**
- Azure Functions: ~$5/month
- Azure OpenAI: ~$10-20/month
- Storage/monitoring: ~$5/month

## Contributing

This is an experimental research project. Contributions, feedback, and ideas are welcome!

**Areas for contribution:**
- Additional failure type analyzers
- Test scenario development
- Documentation improvements
- Code generation implementations

## License

MIT License - see LICENSE for details.

## Author

**Shamsher Khan**
- Senior DevOps Engineer at GlobalLogic (Hitachi)
- IEEE Senior Member
- 15+ years DevOps experience
- DZone Contributor

LinkedIn: [linkedin.com/in/shamsher-khan](https://www.linkedin.com/in/shamsher-khan)

## Acknowledgments

Built for Azure DevOps pipelines in production pharmaceutical environments. Inspired by autonomous agent frameworks and AI-assisted development research.

---

**Project Status:** Active Research | **Current Phase:** Prototype & Testing | **Deployment:** Local Development