################################################################################
# Enterprise Foundry - AI Services Module Outputs
################################################################################

# ======= Document Intelligence =======
output "docintel_id" {
  description = "ID of the Document Intelligence service"
  value       = azurerm_cognitive_account.docintel.id
}

output "docintel_name" {
  description = "Name of the Document Intelligence service"
  value       = azurerm_cognitive_account.docintel.name
}

output "docintel_endpoint" {
  description = "Endpoint of the Document Intelligence service"
  value       = azurerm_cognitive_account.docintel.endpoint
}

output "docintel_private_ip" {
  description = "Private IP address of the Document Intelligence private endpoint"
  value       = azurerm_private_endpoint.docintel.private_service_connection[0].private_ip_address
}

# ======= Azure AI Search =======
output "search_id" {
  description = "ID of the Azure AI Search service"
  value       = azurerm_search_service.search.id
}

output "search_name" {
  description = "Name of the Azure AI Search service"
  value       = azurerm_search_service.search.name
}

output "search_endpoint" {
  description = "Endpoint of the Azure AI Search service (https://<name>.search.windows.net)"
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "search_private_ip" {
  description = "Private IP address of the Azure AI Search private endpoint"
  value       = azurerm_private_endpoint.search.private_service_connection[0].private_ip_address
}

# ======= Managed Identity for Container Apps =======
output "aca_ai_services_identity_id" {
  description = "ID of the managed identity for Container Apps to access AI services"
  value       = azurerm_user_assigned_identity.aca_ai_services.id
}

output "aca_ai_services_identity_client_id" {
  description = "Client ID of the managed identity for Container Apps"
  value       = azurerm_user_assigned_identity.aca_ai_services.client_id
}

output "aca_ai_services_identity_principal_id" {
  description = "Principal ID of the managed identity for Container Apps"
  value       = azurerm_user_assigned_identity.aca_ai_services.principal_id
}

# ======= Microsoft Foundry (AI Services) =======
output "foundry_id" {
  description = "ID of the Microsoft Foundry service"
  value       = azapi_resource.foundry.id
}

output "foundry_name" {
  description = "Name of the Microsoft Foundry service"
  value       = azapi_resource.foundry.name
}

output "foundry_endpoint" {
  description = "Endpoint of the Microsoft Foundry service"
  value       = "https://${var.foundry_name}.cognitiveservices.azure.com/"
}

output "foundry_project_id" {
  description = "ID of the default Foundry project"
  value       = azapi_resource.foundry_project.id
}

output "foundry_project_name" {
  description = "Name of the default Foundry project"
  value       = azapi_resource.foundry_project.name
}

output "embedding_deployment_name" {
  description = "Name of the text embedding deployment"
  value       = azapi_resource.embedding_deployment.name
}

output "gpt4_deployment_name" {
  description = "Name of the GPT-4.1 deployment"
  value       = azapi_resource.gpt4_deployment.name
}

# ======= Connection Info for Container Apps =======
output "container_app_env_vars" {
  description = "Environment variables to configure in Container Apps for AI services"
  value = {
    AZURE_DOCINTEL_ENDPOINT = azurerm_cognitive_account.docintel.endpoint
    AZURE_SEARCH_ENDPOINT   = "https://${azurerm_search_service.search.name}.search.windows.net"
    AZURE_FOUNDRY_ENDPOINT  = "https://${var.foundry_name}.cognitiveservices.azure.com/"
    AZURE_CLIENT_ID         = azurerm_user_assigned_identity.aca_ai_services.client_id
    EMBEDDING_DEPLOYMENT    = azapi_resource.embedding_deployment.name
    GPT4_DEPLOYMENT         = azapi_resource.gpt4_deployment.name
  }
}

# ======= Private DNS Zones =======
output "dns_zone_cognitive_id" {
  description = "ID of the Cognitive Services private DNS zone"
  value       = azurerm_private_dns_zone.cognitive.id
}

output "dns_zone_search_id" {
  description = "ID of the AI Search private DNS zone"
  value       = azurerm_private_dns_zone.search.id
}
