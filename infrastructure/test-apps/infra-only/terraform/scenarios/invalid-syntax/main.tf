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

variable "prefix" {
  default = "test"
}

variable "environment" {
  default = "dev"
}

resource "azurerm_resource_group" "test" {
  name     = "rg-${var.prefix-${var.environment}"  # ← SYNTAX ERROR: Missing closing brace
  location = "eastus"
}
