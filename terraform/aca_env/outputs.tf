output "aca_env_id" {
  description = "Resource ID of the Container Apps environment"
  value       = azurerm_container_app_environment.aca_env.id
}

output "vnet_configuration_summary" {
  description = "Key networking facts from the env"
  value = {
    infrastructure_subnet_id     = azurerm_container_app_environment.aca_env.infrastructure_subnet_id
    internal_load_balancer       = azurerm_container_app_environment.aca_env.internal_load_balancer_enabled
    log_analytics_workspace_id   = azurerm_log_analytics_workspace.laws.id
  }
}