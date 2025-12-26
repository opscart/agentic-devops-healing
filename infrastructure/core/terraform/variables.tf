################################################################################
# Variables for Core Infrastructure
################################################################################

variable "resource_prefix" {
  description = "Prefix for all resource names"
  type        = string
  default     = "agenticdevops"
  
  validation {
    condition     = length(var.resource_prefix) <= 15 && can(regex("^[a-z0-9]+$", var.resource_prefix))
    error_message = "Prefix must be lowercase alphanumeric, max 15 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "azure_region" {
  description = "Azure region for most resources"
  type        = string
  default     = "eastus"
}

variable "openai_region" {
  description = "Azure region for OpenAI (not available in all regions)"
  type        = string
  default     = "eastus"
  
  validation {
    condition = contains([
      "eastus",
      "eastus2",
      "northcentralus",
      "southcentralus",
      "westus",
      "westus3",
      "swedencentral",
      "switzerlandnorth",
      "japaneast",
      "australiaeast",
      "canadaeast",
      "francecentral",
      "uksouth"
    ], var.openai_region)
    error_message = "OpenAI is not available in all regions. Check https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models#model-summary-table-and-region-availability"
  }
}

variable "openai_deployment_name" {
  description = "Name for the GPT-4o deployment"
  type        = string
  default     = "gpt-4o-analyzer"
}

variable "ado_org_url" {
  description = "Azure DevOps organization URL (e.g., https://dev.azure.com/yourorg)"
  type        = string
  default     = ""
}

variable "ado_project_name" {
  description = "Azure DevOps project name"
  type        = string
  default     = ""
}

variable "ado_pat_token" {
  description = "Azure DevOps Personal Access Token (will be stored in Key Vault)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Agentic DevOps Healing"
    ManagedBy   = "Terraform"
    Environment = "dev"
    Owner       = "Shamsher Khan"
    CostCenter  = "Research"
  }
}