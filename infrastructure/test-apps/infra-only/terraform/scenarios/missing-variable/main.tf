terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
}

resource "azurerm_resource_group" "test" {
  name     = "rg-test-missing-var-${formatdate("YYYYMMDD-hhmm", timestamp())}"  # ← Unique name
  location = var.azure_region  # ← ERROR: Variable not defined
}
