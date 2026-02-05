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

variable "acr_name" {
  type        = string
  description = "Name of the Azure Container Registry"
}

variable "app_file_upload_name" {
  type        = string
  description = "Name of the file upload container app"
  default     = "aca-file-upload"
}

variable "file_upload_image_name" {
  type        = string
  description = "Name of the file upload container image in ACR"
  default     = "file-upload-app"
}

variable "file_upload_image_tag" {
  type        = string
  description = "Tag of the file upload container image"
  default     = "latest"
}

variable "docintel_endpoint" {
  type        = string
  description = "Azure Document Intelligence endpoint URL (optional)"
  default     = ""
}

variable "app_sample_agent_name" {
  type        = string
  description = "Name of the sample agent container app"
  default     = "aca-sample-agent"
}

variable "sample_agent_image_name" {
  type        = string
  description = "Name of the sample agent container image in ACR"
  default     = "sample-agent"
}

variable "sample_agent_image_tag" {
  type        = string
  description = "Tag of the sample agent container image"
  default     = "latest"
}

variable "azure_ai_project_endpoint" {
  type        = string
  description = "Azure AI Project endpoint URL for the agent"
  default     = ""
}

variable "azure_ai_model_deployment_name" {
  type        = string
  description = "Azure AI model deployment name (e.g., gpt-4.1)"
  default     = "gpt-4.1"
}
