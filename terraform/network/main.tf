################################################################################
# Enterprise Foundry - Network Module
# 
# Creates:
#   - Resource Groups (network + application)
#   - Hub VNet (simulates corporate hub)
#   - Sandbox VNet with ACA-delegated subnet
#   - On-prem simulation VNet with Ubuntu/nginx VM
#   - VNet Peerings (Hub-Spoke + Direct Spoke-to-Spoke)
#   - Storage Account with Private Endpoint
#   - Azure Container Registry with Private Endpoint
#   - Private DNS Zones for privatelink resolution
#   - Managed Identity for ACA -> ACR pull
################################################################################

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
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
  
  # Use Azure AD for storage data plane operations to avoid shared key issues
  storage_use_azuread = true
}

################################################################################
# Resource Groups
################################################################################

resource "azurerm_resource_group" "net" {
  name     = var.rg_net
  location = var.location
}

resource "azurerm_resource_group" "app" {
  name     = var.rg_app
  location = var.location
}

################################################################################
# Sandbox VNet
################################################################################

resource "azurerm_virtual_network" "sbx" {
  name                = var.sbx_vnet_name
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  address_space       = [var.sbx_vnet_prefix]
}

# Subnet A: ACA Infrastructure (delegated to Microsoft.App/environments, minimum /27)
resource "azurerm_subnet" "sbx_aca" {
  name                 = var.sbx_snet_aca_name
  resource_group_name  = azurerm_resource_group.net.name
  virtual_network_name = azurerm_virtual_network.sbx.name
  address_prefixes     = [var.sbx_snet_aca_prefix]

  delegation {
    name = "aca-delegation"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Subnet B: Private Endpoints (disable endpoint network policies)
resource "azurerm_subnet" "sbx_pe" {
  name                              = var.sbx_snet_pe_name
  resource_group_name               = azurerm_resource_group.net.name
  virtual_network_name              = azurerm_virtual_network.sbx.name
  address_prefixes                  = [var.sbx_snet_pe_prefix]
  private_endpoint_network_policies = "Disabled"
}

################################################################################
# On-prem Simulation VNet
################################################################################

resource "azurerm_virtual_network" "onprem" {
  name                = var.op_vnet_name
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  address_space       = [var.op_vnet_prefix]
}

resource "azurerm_subnet" "onprem" {
  name                 = var.op_snet_name
  resource_group_name  = azurerm_resource_group.net.name
  virtual_network_name = azurerm_virtual_network.onprem.name
  address_prefixes     = [var.op_snet_prefix]
}

################################################################################
# NSG for On-prem Simulation Subnet
################################################################################

resource "azurerm_network_security_group" "onprem" {
  name                = "nsg-onprem-sim"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name

  security_rule {
    name                       = "allow-aca-runtime-http-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = var.sbx_snet_aca_prefix
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "onprem" {
  subnet_id                 = azurerm_subnet.onprem.id
  network_security_group_id = azurerm_network_security_group.onprem.id
}

################################################################################
# On-prem Simulation VM (Ubuntu with nginx)
################################################################################

# Generate SSH key pair
resource "tls_private_key" "vm_ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "azurerm_network_interface" "onprem_vm" {
  name                = "nic-onprem-sim"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.onprem.id
    private_ip_address_allocation = "Dynamic"
  }
}

resource "azurerm_linux_virtual_machine" "onprem" {
  name                = "vm-onprem-sim"
  resource_group_name = azurerm_resource_group.net.name
  location            = azurerm_resource_group.net.location
  size                = var.vm_size
  admin_username      = var.vm_admin_username

  network_interface_ids = [
    azurerm_network_interface.onprem_vm.id
  ]

  admin_ssh_key {
    username   = var.vm_admin_username
    public_key = tls_private_key.vm_ssh.public_key_openssh
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts"
    version   = "latest"
  }

  # Install nginx via cloud-init with HTTPS support (self-signed cert)
  custom_data = base64encode(<<-EOF
    #cloud-config
    package_update: true
    packages:
      - nginx
      - openssl
    runcmd:
      # Generate self-signed certificate
      - mkdir -p /etc/nginx/ssl
      - openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt -subj "/C=DE/ST=State/L=City/O=Test/CN=onprem-sim"
      # Configure nginx for HTTPS
      - |
        cat > /etc/nginx/sites-available/default << 'NGINXCONF'
        server {
            listen 80 default_server;
            listen [::]:80 default_server;
            
            listen 443 ssl default_server;
            listen [::]:443 ssl default_server;
            
            ssl_certificate /etc/nginx/ssl/nginx.crt;
            ssl_certificate_key /etc/nginx/ssl/nginx.key;
            
            root /var/www/html;
            index index.html index.htm;
            
            server_name _;
            
            location / {
                try_files $uri $uri/ =404;
            }
        }
        NGINXCONF
      - systemctl enable nginx
      - systemctl restart nginx
  EOF
  )
}

################################################################################
# Data source: Existing Hub VNet
################################################################################

data "azurerm_virtual_network" "hub" {
  name                = var.hub_vnet_name
  resource_group_name = var.hub_vnet_rg
}

################################################################################
# VNet Peerings: Hub <-> Sandbox
################################################################################

resource "azurerm_virtual_network_peering" "hub_to_sbx" {
  name                         = var.hub_to_sbx_peer
  resource_group_name          = var.hub_vnet_rg
  virtual_network_name         = var.hub_vnet_name
  remote_virtual_network_id    = azurerm_virtual_network.sbx.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  allow_gateway_transit        = true
}

resource "azurerm_virtual_network_peering" "sbx_to_hub" {
  name                         = var.sbx_to_hub_peer
  resource_group_name          = azurerm_resource_group.net.name
  virtual_network_name         = azurerm_virtual_network.sbx.name
  remote_virtual_network_id    = data.azurerm_virtual_network.hub.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  use_remote_gateways          = true

  depends_on = [azurerm_virtual_network_peering.hub_to_sbx]
}

################################################################################
# VNet Peerings: Hub <-> On-prem Simulation
################################################################################

resource "azurerm_virtual_network_peering" "hub_to_onprem" {
  name                         = var.hub_to_op_peer
  resource_group_name          = var.hub_vnet_rg
  virtual_network_name         = var.hub_vnet_name
  remote_virtual_network_id    = azurerm_virtual_network.onprem.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  allow_gateway_transit        = true
}

resource "azurerm_virtual_network_peering" "onprem_to_hub" {
  name                         = var.op_to_hub_peer
  resource_group_name          = azurerm_resource_group.net.name
  virtual_network_name         = azurerm_virtual_network.onprem.name
  remote_virtual_network_id    = data.azurerm_virtual_network.hub.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
  use_remote_gateways          = true

  depends_on = [azurerm_virtual_network_peering.hub_to_onprem]
}

################################################################################
# VNet Peerings: Sandbox <-> On-prem Simulation (Direct)
# VNet peering is non-transitive, so we need direct peering for ACA to reach on-prem
################################################################################

resource "azurerm_virtual_network_peering" "sbx_to_onprem" {
  name                         = "peer-sbx-to-onprem"
  resource_group_name          = azurerm_resource_group.net.name
  virtual_network_name         = azurerm_virtual_network.sbx.name
  remote_virtual_network_id    = azurerm_virtual_network.onprem.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true
}

resource "azurerm_virtual_network_peering" "onprem_to_sbx" {
  name                         = "peer-onprem-to-sbx"
  resource_group_name          = azurerm_resource_group.net.name
  virtual_network_name         = azurerm_virtual_network.onprem.name
  remote_virtual_network_id    = azurerm_virtual_network.sbx.id
  allow_virtual_network_access = true
  allow_forwarded_traffic      = true

  depends_on = [azurerm_virtual_network_peering.sbx_to_onprem]
}

################################################################################
# Private DNS Zone for Blob Storage
################################################################################

resource "azurerm_private_dns_zone" "blob" {
  name                = var.pdz_blob
  resource_group_name = azurerm_resource_group.net.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob_to_sbx" {
  name                  = "pdz-blob-link"
  resource_group_name   = azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.blob.name
  virtual_network_id    = azurerm_virtual_network.sbx.id
  registration_enabled  = false
}

################################################################################
# Storage Account
################################################################################

resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.app.name
  location                 = azurerm_resource_group.app.location
  account_tier             = "Standard"
  account_replication_type = "GRS"
  account_kind             = "StorageV2"

  # Keep public access enabled so Terraform can manage the resource.
  # Network rules are applied separately below to restrict access.
  public_network_access_enabled   = true
  allow_nested_items_to_be_public = false
  
  # Use Azure AD for data plane auth (required with storage_use_azuread = true)
  shared_access_key_enabled       = false  # Disabled - use Azure AD auth only
  default_to_oauth_authentication = true
}

# Apply network rules as a separate resource so the storage account
# is fully created and queryable before locking down access.
resource "azurerm_storage_account_network_rules" "main" {
  storage_account_id = azurerm_storage_account.main.id

  default_action = "Deny"
  bypass         = ["AzureServices"]

  # Allow Microsoft Defender for Storage data scanner
  private_link_access {
    endpoint_resource_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Security/datascanners/storageDataScanner"
  }

  # Ensure container is created before locking down
  depends_on = [azurerm_storage_container.sample]
}

resource "azurerm_storage_container" "sample" {
  name                 = var.storage_container_name
  storage_account_id   = azurerm_storage_account.main.id
  container_access_type = "private"
}

################################################################################
# Private Endpoint for Blob Storage
################################################################################

resource "azurerm_private_endpoint" "blob" {
  name                = "pe-blob-${var.storage_account_name}"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  subnet_id           = azurerm_subnet.sbx_pe.id

  private_service_connection {
    name                           = "conn-blob-${var.storage_account_name}"
    private_connection_resource_id = azurerm_storage_account.main.id
    subresource_names              = ["blob"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dzg-blob-${var.storage_account_name}"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob.id]
  }
}

################################################################################
# Azure Container Registry (Premium for Private Link support)
################################################################################

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.app.name
  location            = azurerm_resource_group.app.location
  sku                 = "Premium"  # Required for Private Link
  admin_enabled       = false      # Use managed identity instead

  # Disable public access - only accessible via Private Endpoint
  public_network_access_enabled = false

  # Enable zone redundancy for production workloads
  zone_redundancy_enabled = false
}

################################################################################
# Private DNS Zone for ACR
################################################################################

resource "azurerm_private_dns_zone" "acr" {
  name                = "privatelink.azurecr.io"
  resource_group_name = azurerm_resource_group.net.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "acr_to_sbx" {
  name                  = "pdz-acr-link"
  resource_group_name   = azurerm_resource_group.net.name
  private_dns_zone_name = azurerm_private_dns_zone.acr.name
  virtual_network_id    = azurerm_virtual_network.sbx.id
  registration_enabled  = false
}

################################################################################
# Private Endpoint for ACR
################################################################################

resource "azurerm_private_endpoint" "acr" {
  name                = "pe-acr-${var.acr_name}"
  location            = azurerm_resource_group.net.location
  resource_group_name = azurerm_resource_group.net.name
  subnet_id           = azurerm_subnet.sbx_pe.id

  private_service_connection {
    name                           = "conn-acr-${var.acr_name}"
    private_connection_resource_id = azurerm_container_registry.acr.id
    subresource_names              = ["registry"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "dzg-acr-${var.acr_name}"
    private_dns_zone_ids = [azurerm_private_dns_zone.acr.id]
  }
}

################################################################################
# User Assigned Managed Identity for ACA to pull from ACR
################################################################################

resource "azurerm_user_assigned_identity" "aca_acr_pull" {
  name                = "id-aca-acr-pull"
  location            = azurerm_resource_group.app.location
  resource_group_name = azurerm_resource_group.app.name
}

# Grant AcrPull role to the managed identity
resource "azurerm_role_assignment" "aca_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aca_acr_pull.principal_id
}
