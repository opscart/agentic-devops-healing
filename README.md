# Agentic DevOps Healing

> **Autonomous AI-powered system for detecting and remediating Azure DevOps pipeline failures**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Azure](https://img.shields.io/badge/Azure-0078D4?logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com)
[![Terraform](https://img.shields.io/badge/Terraform-7B42BC?logo=terraform&logoColor=white)](https://www.terraform.io/)

## 🎯 Overview

An experimental research project exploring autonomous remediation of DevOps pipeline failures using Large Language Models (LLMs). The system analyzes failure logs, identifies root causes, and automatically generates fixes for infrastructure and build issues.

**Current Status:** Phase 1 - Infrastructure Healing (Terraform/YAML)

## 🏗️ Architecture
```
Pipeline Failure → Webhook → AI Agent → Root Cause Analysis → Auto-Fix PR
```

The agent uses Azure OpenAI (GPT-4o/o1) to:
1. Parse build logs and error messages
2. Compare with last successful build
3. Classify failure type (config, code, infra, test)
4. Generate remediation code
5. Create Pull Request with fix

## 📋 Current Capabilities

### ✅ Infrastructure Healer (Phase 1)
- Terraform missing variables
- Azure region typos
- Pipeline YAML syntax errors
- Terraform state conflicts

### 🚧 Planned Capabilities
- **Build Healer:** Maven/Gradle dependency conflicts, Docker build failures
- **Deployment Healer:** AKS ImagePullBackOff, App Service issues
- **Test Healer:** Flaky test detection, integration test failures

## 🚀 Quick Start

### Prerequisites
- Azure subscription (free $200 credit available)
- Azure CLI installed
- Terraform >= 1.5
- Python 3.11+
- Azure DevOps organization

### Deploy Agent Infrastructure
```bash
# Configure Azure credentials
./scripts/setup/configure-azure-credentials.sh

# Deploy core agent infrastructure
cd infrastructure/core/terraform
./scripts/deploy.sh

# Get webhook URL
./scripts/outputs.sh
```

### Test First Scenario
```bash
# Deploy test app with broken Terraform
cd infrastructure/test-apps/infra-only/terraform/scenarios/missing-variable
terraform init
terraform apply  # This will fail

# Check Azure DevOps pipeline - agent should create fix PR
```

Full setup guide: [docs/setup/01-azure-prerequisites.md](docs/setup/01-azure-prerequisites.md)

## 📊 Repository Structure
```
agentic-devops-healing/
├── infrastructure/
│   ├── core/                   # Agent infrastructure (Function, OpenAI, Storage)
│   ├── modules/                # Reusable Terraform modules
│   └── test-apps/              # Test workloads with deliberate failures
├── src/
│   ├── agents/                 # Specialized healing agents
│   │   ├── infra-healer/      # Terraform/YAML (current)
│   │   ├── build-healer/      # Maven/Docker (planned)
│   │   └── deployment-healer/ # AKS/App Service (planned)
│   └── shared/                 # Common libraries (ADO, OpenAI, Git)
├── scenarios/                  # Test case documentation
├── docs/                       # Architecture, setup guides, research
└── scripts/                    # Automation scripts
```

## 💰 Cost Estimation

**Development (destroy daily):**
- Agent infrastructure: ~$5/month
- OpenAI API: ~$10-20/month
- Test resources: ~$0 (destroyed after testing)

**Total: ~$15-25/month**

See [docs/guides/cost-optimization.md](docs/guides/cost-optimization.md) for details.

## 📖 Documentation

- [System Architecture](docs/architecture/system-overview.md)
- [Setup Guide](docs/setup/01-azure-prerequisites.md)
- [Adding New Agents](docs/guides/adding-new-agent.md)
- [Test Scenarios](scenarios/infra/)

## 🔬 Research

This project serves as the foundation for academic research on AI-assisted DevOps automation:

- IEEE paper: "Autonomous Infrastructure Remediation using Large Language Models"
- Metrics tracking: RCA accuracy, MTTR reduction, auto-fix success rate
- Experiment log: [docs/research/experiment-log.md](docs/research/experiment-log.md)

## 🤝 Contributing

This is an experimental research project. Contributions, ideas, and feedback are welcome!

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 👤 Author

**Shamsher Khan**
- Senior DevOps Engineer at GlobalLogic (Hitachi)
- IEEE Senior Member
- LinkedIn: [linkedin.com/in/shamsher-khan](https://www.linkedin.com/in/shamsher-khan)

## 🙏 Acknowledgments

- Built for Azure DevOps pipelines in pharmaceutical production environments
- Inspired by autonomous agent frameworks and AI-assisted development tools

---

**Status:** Active Development | **Phase:** 1 of 4 | **Last Updated:** December 2024
