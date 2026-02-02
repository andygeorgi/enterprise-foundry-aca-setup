################################################################################
# Enterprise Foundry - ACA Environment Module
#
# Creates:
#   - Log Analytics Workspace
#   - Azure Container Apps Managed Environment (VNet-injected, internal LB)
#
# Prerequisites: network module must be deployed first
################################################################################

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.subscription_id
}

# --- Data lookups: existing subnets in sandbox VNet ---

data "azurerm_subnet" "aca" {
  name                 = var.subnet_aca
  virtual_network_name = var.vnet_name
  resource_group_name  = var.rg_net
}

# --- Log Analytics workspace required by ACA env ---

resource "azurerm_log_analytics_workspace" "laws" {
  name                = var.laws_name
  location            = var.location
  resource_group_name = var.rg_app
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# --- Azure Container Apps Managed Environment (VNet-injected) ---

resource "azurerm_container_app_environment" "aca_env" {
  name                         = var.aca_env_name
  location                     = var.location
  resource_group_name          = var.rg_app

  # Keep the environment private (internal load balancer)
  internal_load_balancer_enabled = true

  # ACA infrastructure subnet – minimum /27 required
  infrastructure_subnet_id = data.azurerm_subnet.aca.id

  # Wire diagnostics
  log_analytics_workspace_id = azurerm_log_analytics_workspace.laws.id

  # Zone redundancy optional; toggle if needed
  zone_redundancy_enabled = false
}