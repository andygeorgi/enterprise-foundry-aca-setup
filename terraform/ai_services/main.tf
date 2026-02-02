################################################################################
# Enterprise Foundry - AI Services Module
#
# Creates:
#   - Azure Document Intelligence with Private Endpoint
#   - Azure AI Search with Private Endpoint
#   - Private DNS Zones for all services
#   - Managed Identity for Container Apps to access AI Services
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
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
  subscription_id = var.subscription_id
}

################################################################################
# Data Sources - Existing Resources from Network Module
################################################################################

data "azurerm_resource_group" "app" {
  name = var.rg_app
}

data "azurerm_resource_group" "net" {
  name = var.rg_net
}

data "azurerm_virtual_network" "sbx" {
  name                = var.sbx_vnet_name
  resource_group_name = var.rg_net
}

data "azurerm_subnet" "pe" {
  name                 = var.sbx_snet_pe_name
  virtual_network_name = var.sbx_vnet_name
  resource_group_name  = var.rg_net
}

# Hub VNet for DNS zone linking (for VPN/ExpressRoute access)
data "azurerm_virtual_network" "hub" {
  name                = var.hub_vnet_name
  resource_group_name = var.hub_vnet_rg
}

# Storage Account (for AI Search indexing)
data "azurerm_storage_account" "main" {
  name                = var.storage_account_name
  resource_group_name = var.rg_app
}

################################################################################
# Azure Document Intelligence (Form Recognizer)
################################################################################

resource "azurerm_cognitive_account" "docintel" {
  name                  = var.docintel_name
  location              = data.azurerm_resource_group.app.location
  resource_group_name   = data.azurerm_resource_group.app.name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = var.docintel_name

  # Disable public access - only via Private Endpoint
  public_network_access_enabled = false

  network_acls {
    default_action = "Deny"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

################################################################################
# Private DNS Zone for Cognitive Services (Document Intelligence)
################################################################################

resource "azurerm_private_dns_zone" "cognitive" {
  name                = "privatelink.cognitiveservices.azure.com"
  resource_group_name = data.azurerm_resource_group.net.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cognitive_to_sbx" {
  name                  = "pdz-cognitive-link-sbx"
  resource_group_name   = data.azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.cognitive.name
  virtual_network_id    = data.azurerm_virtual_network.sbx.id
  registration_enabled  = false
}

# Link to Hub VNet for DNS resolution via VPN/ExpressRoute
resource "azurerm_private_dns_zone_virtual_network_link" "cognitive_to_hub" {
  name                  = "pdz-cognitive-link-hub"
  resource_group_name   = data.azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.cognitive.name
  virtual_network_id    = data.azurerm_virtual_network.hub.id
  registration_enabled  = false
}

################################################################################
# Private Endpoint for Document Intelligence
################################################################################

resource "azurerm_private_endpoint" "docintel" {
  name                = "pe-docintel-${var.docintel_name}"
  location            = data.azurerm_resource_group.net.location
  resource_group_name = data.azurerm_resource_group.net.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "conn-docintel-${var.docintel_name}"
    private_connection_resource_id = azurerm_cognitive_account.docintel.id
    subresource_names              = ["account"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dzg-docintel-${var.docintel_name}"
    private_dns_zone_ids = [azurerm_private_dns_zone.cognitive.id]
  }

  tags = var.tags
}

################################################################################
# Azure AI Search
################################################################################

resource "azurerm_search_service" "search" {
  name                          = var.search_name
  location                      = data.azurerm_resource_group.app.location
  resource_group_name           = data.azurerm_resource_group.app.name
  sku                           = var.search_sku
  replica_count                 = 1
  partition_count               = 1
  semantic_search_sku           = "standard"  # Enable semantic search
  
  # Disable public access - only via Private Endpoint
  public_network_access_enabled = false

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

################################################################################
# Private DNS Zone for Azure AI Search
################################################################################

resource "azurerm_private_dns_zone" "search" {
  name                = "privatelink.search.windows.net"
  resource_group_name = data.azurerm_resource_group.net.name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "search_to_sbx" {
  name                  = "pdz-search-link-sbx"
  resource_group_name   = data.azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.search.name
  virtual_network_id    = data.azurerm_virtual_network.sbx.id
  registration_enabled  = false
}

# Link to Hub VNet for DNS resolution via VPN/ExpressRoute
resource "azurerm_private_dns_zone_virtual_network_link" "search_to_hub" {
  name                  = "pdz-search-link-hub"
  resource_group_name   = data.azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.search.name
  virtual_network_id    = data.azurerm_virtual_network.hub.id
  registration_enabled  = false
}

################################################################################
# Private Endpoint for Azure AI Search
################################################################################

resource "azurerm_private_endpoint" "search" {
  name                = "pe-search-${var.search_name}"
  location            = data.azurerm_resource_group.net.location
  resource_group_name = data.azurerm_resource_group.net.name
  subnet_id           = data.azurerm_subnet.pe.id

  private_service_connection {
    name                           = "conn-search-${var.search_name}"
    private_connection_resource_id = azurerm_search_service.search.id
    subresource_names              = ["searchService"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dzg-search-${var.search_name}"
    private_dns_zone_ids = [azurerm_private_dns_zone.search.id]
  }

  tags = var.tags
}

################################################################################
# User Assigned Managed Identity for Container Apps to access AI Services
################################################################################

resource "azurerm_user_assigned_identity" "aca_ai_services" {
  name                = "id-aca-ai-services"
  location            = data.azurerm_resource_group.app.location
  resource_group_name = data.azurerm_resource_group.app.name
  tags                = var.tags
}

################################################################################
# RBAC: Container Apps Identity -> Document Intelligence
################################################################################

resource "azurerm_role_assignment" "aca_docintel_user" {
  scope                = azurerm_cognitive_account.docintel.id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.aca_ai_services.principal_id
}

################################################################################
# RBAC: Container Apps Identity -> AI Search
################################################################################

resource "azurerm_role_assignment" "aca_search_contributor" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.aca_ai_services.principal_id
}

resource "azurerm_role_assignment" "aca_search_reader" {
  scope                = azurerm_search_service.search.id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.aca_ai_services.principal_id
}

################################################################################
# RBAC: AI Search -> Storage Account (for indexing blobs)
################################################################################

resource "azurerm_role_assignment" "search_storage_reader" {
  scope                = data.azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.search.identity[0].principal_id
}

################################################################################
# RBAC: Document Intelligence -> Storage Account (for reading documents)
################################################################################

resource "azurerm_role_assignment" "docintel_storage_reader" {
  scope                = data.azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_cognitive_account.docintel.identity[0].principal_id
}
