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
  description = "Resource group name that contains the networking resources"
}

variable "rg_app" {
  type        = string
  description = "Resource group name for the ACA environment and container apps"
}

variable "aca_env_name" {
  type        = string
  description = "Name of the existing ACA managed environment"
}

variable "app_onprem_name" {
  type        = string
  description = "Name of the on-prem connectivity test container app"
  default     = "aca-onprem-connectivity-test"
}

variable "app_pe_storage_name" {
  type        = string
  description = "Name of the private endpoint storage test container app"
  default     = "aca-pe-storage-test"
}

variable "storage_account_name" {
  type        = string
  description = "Name of the storage account to test connectivity"
}

variable "storage_container_name" {
  type        = string
  description = "Name of the blob container to list"
  default     = "test"
}
