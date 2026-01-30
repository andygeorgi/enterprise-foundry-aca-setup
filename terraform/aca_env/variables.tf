variable "subscription_id" {
  type        = string
  description = "Azure Subscription ID"
}

variable "location" {
  type        = string
  description = "Azure region (e.g., westeurope)"
}

variable "rg_net" {
  type        = string
  description = "Resource group name that contains the sandbox VNet"
}

variable "rg_app" {
  type        = string
  description = "Resource group name for the ACA environment + LA workspace"
}

variable "vnet_name" {
  type        = string
  description = "Sandbox VNet name (e.g., vnet-hexpert-sbx-weu)"
}

variable "subnet_aca" {
  type        = string
  description = "ACA infrastructure subnet name (delegated to Microsoft.App/environments, minimum /27)"
}

variable "aca_env_name" {
  type        = string
  description = "ACA managed environment name (e.g., cae-hexpert-sbx-weu)"
}

variable "laws_name" {
  type        = string
  description = "Log Analytics workspace name (e.g., laws-hexpert-sbx-weu)"
}