################################################################################
# Enterprise Foundry - Network Module Variables
################################################################################

# ======= Subscription & Location =======
variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
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
  default     = "rg-foundry-sbx-net"
}

variable "rg_app" {
  type        = string
  description = "Resource group for application resources"
  default     = "rg-foundry-sbx-app"
}

# ======= Hub VNet (existing) =======
variable "hub_vnet_rg" {
  type        = string
  description = "Resource group containing the hub VNet"
  default     = "net-shared-test-westeurope-001"
}

variable "hub_vnet_name" {
  type        = string
  description = "Name of the existing hub VNet"
  default     = "net-shared-gateway-westeurope-001"
}

# ======= Sandbox VNet & Subnets =======
variable "sbx_vnet_name" {
  type        = string
  description = "Sandbox VNet name"
  default     = "vnet-foundry-sbx-weu"
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
  default     = "stfoundrysbx"
}

# ======= Azure Container Registry =======
variable "acr_name" {
  type        = string
  description = "Azure Container Registry name (must be globally unique, alphanumeric only)"
  default     = "acrfoundrysbx"
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
