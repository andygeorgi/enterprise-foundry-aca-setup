################################################################################
# Enterprise Foundry - AI Services Module Variables
################################################################################

# ======= Subscription & Location =======
variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
}

# ======= Resource Groups (from network module) =======
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

# ======= Network Resources (from network module) =======
variable "sbx_vnet_name" {
  type        = string
  description = "Sandbox VNet name"
  default     = "vnet-foundry-sbx-weu"
}

variable "sbx_snet_pe_name" {
  type        = string
  description = "Private Endpoints subnet name"
  default     = "snet-private-endpoints"
}

# ======= Hub VNet (for DNS zone linking) =======
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

# ======= Storage Account (from network module) =======
variable "storage_account_name" {
  type        = string
  description = "Storage account name for AI Search indexing"
  default     = "stfoundrysbx"
}

# ======= Document Intelligence =======
variable "docintel_name" {
  type        = string
  description = "Document Intelligence service name (must be globally unique)"
  default     = "docintel-foundry-sbx"
}

# ======= Azure AI Search =======
variable "search_name" {
  type        = string
  description = "Azure AI Search service name (must be globally unique)"
  default     = "search-foundry-sbx"
}

variable "search_sku" {
  type        = string
  description = "Azure AI Search SKU (basic, standard, standard2, standard3)"
  default     = "basic"  # For sandbox; use 'standard' for production
}

# ======= Tags =======
variable "tags" {
  type        = map(string)
  description = "Tags to apply to all resources"
  default = {
    environment = "sandbox"
    project     = "foundry"
    managedBy   = "terraform"
  }
}
