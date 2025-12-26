################################################################################
# Agentic DevOps Healing - Core Infrastructure
# Creates: Function App, Azure OpenAI, Storage, Key Vault, Monitoring
################################################################################

terraform {
  required_version = ">= 1.5"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

################################################################################
# Random suffix for globally unique names
################################################################################
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

################################################################################
# Resource Group
################################################################################
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.resource_prefix}-${var.environment}"
  location = var.azure_region
  
  tags = merge(var.common_tags, {
    Purpose = "Agentic DevOps Healing Agent"
  })
}

################################################################################
# Storage Account (Required by Functions + Log Storage)
################################################################################
resource "azurerm_storage_account" "main" {
  name                     = "st${var.resource_prefix}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  # Enable for storing build logs
  blob_properties {
    versioning_enabled = false
    
    delete_retention_policy {
      days = 7
    }
  }
  
  tags = var.common_tags
}

# Container for build logs
resource "azurerm_storage_container" "build_logs" {
  name                  = "build-logs"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Container for Terraform state (optional - for test apps)
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Queue for async processing (if needed in future)
resource "azurerm_storage_queue" "failures" {
  name                 = "pipeline-failures"
  storage_account_name = azurerm_storage_account.main.name
}

################################################################################
# Log Analytics Workspace (Required by App Insights)
################################################################################
resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${var.resource_prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  
  tags = var.common_tags
}

################################################################################
# Application Insights (Monitoring for Function App)
################################################################################
resource "azurerm_application_insights" "main" {
  name                = "appi-${var.resource_prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  
  tags = var.common_tags
}

################################################################################
# Azure OpenAI Cognitive Services
################################################################################
resource "azurerm_cognitive_account" "openai" {
  name                = "oai-${var.resource_prefix}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.openai_region  # Not all regions support OpenAI
  kind                = "OpenAI"
  sku_name            = "S0"
  
  tags = var.common_tags
}

# Deploy GPT-4o model
resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = var.openai_deployment_name
  cognitive_account_id = azurerm_cognitive_account.openai.id
  
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"  # Latest stable version
  }
  
  sku {
    name     = "Standard"
    capacity = 10  # 10K tokens per minute
  }
}

################################################################################
# Key Vault (Store Secrets)
################################################################################
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                       = "kv-${var.resource_prefix}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  
  # Allow access from Azure services
  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }
  
  tags = var.common_tags
}

# Grant current user access to Key Vault (for initial setup)
resource "azurerm_key_vault_access_policy" "current_user" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id
  
  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover"
  ]
}

# Store OpenAI API key in Key Vault
resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_key_vault_access_policy.current_user]
}

# Placeholder for Azure DevOps PAT (you'll set this manually)
resource "azurerm_key_vault_secret" "ado_pat" {
  name         = "ado-pat"
  value        = var.ado_pat_token != "" ? var.ado_pat_token : "REPLACE_ME_AFTER_DEPLOYMENT"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [azurerm_key_vault_access_policy.current_user]
  
  lifecycle {
    ignore_changes = [value]  # Don't overwrite if manually updated
  }
}

################################################################################
# App Service Plan (Consumption - Serverless)
################################################################################
resource "azurerm_service_plan" "main" {
  name                = "asp-${var.resource_prefix}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1"  # Consumption plan (cheapest)
  
  tags = var.common_tags
}

################################################################################
# Function App (The AI Agent)
################################################################################
resource "azurerm_linux_function_app" "main" {
  name                       = "func-${var.resource_prefix}-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  
  identity {
    type = "SystemAssigned"
  }
  
  site_config {
    application_stack {
      python_version = "3.11"
    }
    
    # CORS settings (if you build a dashboard later)
    cors {
      allowed_origins = ["https://portal.azure.com"]
    }
    
    application_insights_key               = azurerm_application_insights.main.instrumentation_key
    application_insights_connection_string = azurerm_application_insights.main.connection_string
  }
  
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"       = "python"
    "AzureWebJobsStorage"            = azurerm_storage_account.main.primary_connection_string
    "WEBSITE_RUN_FROM_PACKAGE"       = "1"
    
    # Azure OpenAI settings
    "OPENAI_ENDPOINT"                = azurerm_cognitive_account.openai.endpoint
    "OPENAI_DEPLOYMENT_NAME"         = var.openai_deployment_name
    "OPENAI_API_VERSION"             = "2024-08-01-preview"
    
    # Key Vault reference for OpenAI key
    "OPENAI_API_KEY"                 = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_key.id})"
    
    # Key Vault reference for ADO PAT
    "ADO_PAT"                        = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.ado_pat.id})"
    
    # Azure DevOps settings (set via variables)
    "ADO_ORG_URL"                    = var.ado_org_url
    "ADO_PROJECT_NAME"               = var.ado_project_name
    
    # Storage settings
    "STORAGE_CONNECTION_STRING"      = azurerm_storage_account.main.primary_connection_string
    "LOG_CONTAINER_NAME"             = azurerm_storage_container.build_logs.name
    
    # Application Insights
    "APPINSIGHTS_INSTRUMENTATIONKEY" = azurerm_application_insights.main.instrumentation_key
  }
  
  tags = var.common_tags
}

################################################################################
# Grant Function App access to Key Vault
################################################################################
resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = azurerm_linux_function_app.main.identity[0].tenant_id
  object_id    = azurerm_linux_function_app.main.identity[0].principal_id
  
  secret_permissions = [
    "Get",
    "List"
  ]
  
  depends_on = [azurerm_linux_function_app.main]
}