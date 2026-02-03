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

output "file_upload_app" {
  description = "File upload container app details"
  value = {
    name         = azurerm_container_app.file_upload.name
    fqdn         = azurerm_container_app.file_upload.ingress[0].fqdn
    url          = "https://${azurerm_container_app.file_upload.ingress[0].fqdn}"
    image        = "${data.azurerm_container_registry.acr.login_server}/${var.file_upload_image_name}:${var.file_upload_image_tag}"
  }
}

output "logs_commands" {
  description = "Commands to stream container app logs"
  value = {
    onprem_test     = "az containerapp logs show -g ${var.rg_app} -n ${azurerm_container_app.onprem_test.name} --follow"
    pe_storage_test = "az containerapp logs show -g ${var.rg_app} -n ${azurerm_container_app.pe_storage_test.name} --follow"
    file_upload     = "az containerapp logs show -g ${var.rg_app} -n ${azurerm_container_app.file_upload.name} --follow"
  }
}
