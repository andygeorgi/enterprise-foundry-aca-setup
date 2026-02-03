################################################################################
# Enterprise Foundry - Network Module Variables
################################################################################

# ======= Subscription & Location =======
variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
  default     = "4b026ed5-a12a-4349-b2d1-870c7144e09d"
}

variable "location" {
  type        = string
  description = "Azure region"
  default     = "westeurope"
}

# ======= Resource Groups =======
variable "rg_net" {
  type        = string
  description = "Resource group for networking resources"
  default     = "rg-hexpert-sbx-net"
}

variable "rg_app" {
  type        = string
  description = "Resource group for application resources"
  default     = "rg-hexpert-sbx-app"
}

# ======= Hub VNet Configuration =======
variable "create_hub_vnet" {
  type        = bool
  description = "Create a new hub VNet with VPN Gateway. Set to false to use an existing hub VNet."
  default     = true
}

variable "existing_hub_vnet_rg" {
  type        = string
  description = "Resource group of existing hub VNet (only used if create_hub_vnet = false)"
  default     = ""
}

# ======= Hub VNet (corporate hub with VPN Gateway) =======
variable "hub_vnet_name" {
  type        = string
  description = "Name of the hub VNet"
  default     = "vnet-hub-weu"
}

variable "hub_vnet_prefix" {
  type        = string
  description = "Hub VNet address prefix"
  default     = "10.0.0.0/16"
}

variable "hub_snet_gw_prefix" {
  type        = string
  description = "Hub Gateway subnet prefix (for VPN Gateway)"
  default     = "10.0.1.0/24"
}

variable "hub_snet_fw_prefix" {
  type        = string
  description = "Hub Firewall subnet prefix (optional, for Azure Firewall)"
  default     = "10.0.2.0/24"
}

# ======= VPN Gateway Configuration =======
variable "create_vpn_gateway" {
  type        = bool
  description = "Create VPN Gateway in the hub VNet. Only applicable if create_hub_vnet = true."
  default     = true
}

variable "use_hub_gateway" {
  type        = bool
  description = "Whether spoke VNets should use the hub's VPN gateway (use_remote_gateways). Set to true if the hub has an existing VPN/ExpressRoute gateway."
  default     = true
}

variable "vpn_gateway_sku" {
  type        = string
  description = "VPN Gateway SKU (VpnGw1, VpnGw2, VpnGw3, VpnGw1AZ, etc.)"
  default     = "VpnGw1"

  validation {
    condition     = contains(["VpnGw1", "VpnGw2", "VpnGw3", "VpnGw1AZ", "VpnGw2AZ", "VpnGw3AZ"], var.vpn_gateway_sku)
    error_message = "VPN Gateway SKU must be one of: VpnGw1, VpnGw2, VpnGw3, VpnGw1AZ, VpnGw2AZ, VpnGw3AZ"
  }
}

variable "vpn_client_address_space" {
  type        = string
  description = "Address space for VPN clients (Point-to-Site). This range should not overlap with any VNet."
  default     = "172.16.0.0/24"
}

variable "vpn_root_cert_name" {
  type        = string
  description = "Name for the root certificate used for P2S VPN authentication"
  default     = "P2SRootCert"
}

variable "vpn_root_cert_data" {
  type        = string
  description = "Base64 encoded public certificate data (without BEGIN/END CERTIFICATE headers)"
  default     = ""
  sensitive   = true
}

# ======= Sandbox VNet & Subnets =======
variable "sbx_vnet_name" {
  type        = string
  description = "Sandbox VNet name"
  default     = "vnet-hexpert-sbx-weu"
}

variable "sbx_vnet_prefix" {
  type        = string
  description = "Sandbox VNet address prefix"
  default     = "10.7.0.0/26"
}

variable "sbx_snet_aca_name" {
  type        = string
  description = "ACA Infrastructure subnet name"
  default     = "snet-aca-infra"
}

variable "sbx_snet_aca_prefix" {
  type        = string
  description = "ACA Infrastructure subnet prefix (minimum /27 required)"
  default     = "10.7.0.0/27"
}

variable "sbx_snet_pe_name" {
  type        = string
  description = "Private Endpoints subnet name"
  default     = "snet-private-endpoints"
}

variable "sbx_snet_pe_prefix" {
  type        = string
  description = "Private Endpoints subnet prefix"
  default     = "10.7.0.32/28"
}

variable "sbx_snet_acr_agent_name" {
  type        = string
  description = "ACR build agent pool subnet name"
  default     = "snet-acr-agents"
}

variable "sbx_snet_acr_agent_prefix" {
  type        = string
  description = "ACR build agent pool subnet prefix"
  default     = "10.7.0.48/28"
}

# ======= On-prem simulation VNet & Subnet =======
variable "op_vnet_name" {
  type        = string
  description = "On-prem simulation VNet name"
  default     = "vnet-onprem-sim-weu"
}

variable "op_vnet_prefix" {
  type        = string
  description = "On-prem simulation VNet prefix"
  default     = "10.7.1.0/24"
}

variable "op_snet_name" {
  type        = string
  description = "On-prem simulation subnet name"
  default     = "snet-onprem-sim"
}

variable "op_snet_prefix" {
  type        = string
  description = "On-prem simulation subnet prefix"
  default     = "10.7.1.0/24"
}

# ======= Peering names =======
variable "hub_to_sbx_peer" {
  type        = string
  description = "Hub to Sandbox peering name"
  default     = "peer-hub-to-sbx"
}

variable "sbx_to_hub_peer" {
  type        = string
  description = "Sandbox to Hub peering name"
  default     = "peer-sbx-to-hub"
}

variable "hub_to_op_peer" {
  type        = string
  description = "Hub to On-prem peering name"
  default     = "peer-hub-to-onprem"
}

variable "op_to_hub_peer" {
  type        = string
  description = "On-prem to Hub peering name"
  default     = "peer-onprem-to-hub"
}

# ======= Storage Account =======
variable "storage_account_name" {
  type        = string
  description = "Storage account name (must be globally unique)"
  default     = "sthexpertsbx2898"
}

# ======= Azure Container Registry =======
variable "acr_name" {
  type        = string
  description = "Azure Container Registry name (must be globally unique, alphanumeric only)"
  default     = "acrhexpertsbx2898"
}

variable "storage_container_name" {
  type        = string
  description = "Storage container name"
  default     = "sample"
}

# ======= Private DNS Zones =======
variable "pdz_blob" {
  type        = string
  description = "Private DNS zone for blob storage"
  default     = "privatelink.blob.core.windows.net"
}

# ======= VM Settings =======
variable "vm_admin_username" {
  type        = string
  description = "Admin username for the on-prem simulation VM"
  default     = "azureuser"
}

variable "vm_size" {
  type        = string
  description = "VM size for the on-prem simulation VM"
  default     = "Standard_B1s"
}
