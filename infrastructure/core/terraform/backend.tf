################################################################################
# Terraform Backend Configuration
# Stores state in Azure Storage (create storage account first)
################################################################################

# Uncomment after creating backend storage account
# Run: ./scripts/setup-backend.sh first

# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-terraform-state"
#     storage_account_name = "sttfstate<random>"
#     container_name       = "tfstate"
#     key                  = "agentic-devops-healing/core.tfstate"
#   }
# }