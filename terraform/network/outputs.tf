################################################################################
# Outputs
################################################################################

# Resource Groups
output "rg_net_name" {
  description = "Name of the networking resource group"
  value       = azurerm_resource_group.net.name
}

output "rg_app_name" {
  description = "Name of the application resource group"
  value       = azurerm_resource_group.app.name
}

# Hub VNet
output "hub_vnet_id" {
  description = "ID of the Hub VNet"
  value       = local.hub_vnet_id
}

output "hub_vnet_name" {
  description = "Name of the Hub VNet"
  value       = local.hub_vnet_name
}

output "hub_vnet_created" {
  description = "Whether a new hub VNet was created (true) or existing was used (false)"
  value       = var.create_hub_vnet
}

# VPN Gateway
output "vpn_gateway_id" {
  description = "ID of the VPN Gateway (if created)"
  value       = var.create_hub_vnet && var.create_vpn_gateway ? azurerm_virtual_network_gateway.vpn[0].id : null
}

output "vpn_gateway_public_ip" {
  description = "Public IP address of the VPN Gateway (if created)"
  value       = var.create_hub_vnet && var.create_vpn_gateway ? azurerm_public_ip.vpn_gateway[0].ip_address : null
}

output "vpn_client_address_space" {
  description = "Address space allocated to VPN clients (if VPN Gateway created)"
  value       = var.create_hub_vnet && var.create_vpn_gateway ? var.vpn_client_address_space : null
}

# Sandbox VNet
output "sbx_vnet_id" {
  description = "ID of the Sandbox VNet"
  value       = azurerm_virtual_network.sbx.id
}

output "sbx_vnet_name" {
  description = "Name of the Sandbox VNet"
  value       = azurerm_virtual_network.sbx.name
}

# Subnets
output "sbx_snet_aca_id" {
  description = "ID of the ACA Infrastructure subnet"
  value       = azurerm_subnet.sbx_aca.id
}

output "sbx_snet_pe_id" {
  description = "ID of the Private Endpoints subnet"
  value       = azurerm_subnet.sbx_pe.id
}

# On-prem Simulation
output "onprem_vnet_id" {
  description = "ID of the On-prem simulation VNet"
  value       = azurerm_virtual_network.onprem.id
}

output "onprem_vm_private_ip" {
  description = "Private IP address of the on-prem simulation VM"
  value       = azurerm_network_interface.onprem_vm.private_ip_address
}

output "onprem_vm_ssh_private_key" {
  description = "SSH private key for the on-prem VM (sensitive)"
  value       = tls_private_key.vm_ssh.private_key_pem
  sensitive   = true
}

# Storage Account
output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint URL"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

# Private Endpoint
output "blob_private_endpoint_ip" {
  description = "Private IP address of the blob private endpoint"
  value       = azurerm_private_endpoint.blob.private_service_connection[0].private_ip_address
}

# Private DNS Zone
output "blob_private_dns_zone_id" {
  description = "ID of the blob private DNS zone"
  value       = azurerm_private_dns_zone.blob.id
}

################################################################################
# ACR Outputs
################################################################################

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  description = "ACR login server URL"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_private_endpoint_ip" {
  description = "Private IP address of the ACR private endpoint"
  value       = azurerm_private_endpoint.acr.private_service_connection[0].private_ip_address
}

output "aca_acr_pull_identity_id" {
  description = "Resource ID of the managed identity for ACA to pull from ACR"
  value       = azurerm_user_assigned_identity.aca_acr_pull.id
}

output "aca_acr_pull_identity_client_id" {
  description = "Client ID of the managed identity for ACA to pull from ACR"
  value       = azurerm_user_assigned_identity.aca_acr_pull.client_id
}
