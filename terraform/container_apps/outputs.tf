output "onprem_test_app" {
  description = "On-prem connectivity test container app details"
  value = {
    name         = azurerm_container_app.onprem_test.name
    fqdn         = azurerm_container_app.onprem_test.ingress[0].fqdn
    target_vm_ip = data.azurerm_network_interface.onprem_nic.private_ip_address
  }
}

output "pe_storage_test_app" {
  description = "Private endpoint storage test container app details"
  value = {
    name                 = azurerm_container_app.pe_storage_test.name
    fqdn                 = azurerm_container_app.pe_storage_test.ingress[0].fqdn
    target_storage       = var.storage_account_name
    principal_id         = azurerm_container_app.pe_storage_test.identity[0].principal_id
  }
}

output "logs_commands" {
  description = "Commands to stream container app logs"
  value = {
    onprem_test     = "az containerapp logs show -g ${var.rg_app} -n ${azurerm_container_app.onprem_test.name} --follow"
    pe_storage_test = "az containerapp logs show -g ${var.rg_app} -n ${azurerm_container_app.pe_storage_test.name} --follow"
  }
}
