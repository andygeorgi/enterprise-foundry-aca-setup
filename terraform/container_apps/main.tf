################################################################################
# Enterprise Foundry - Container Apps Module (Optional Test Apps)
#
# Creates:
#   - On-prem connectivity test container app
#   - Storage private endpoint test container app
#
# Prerequisites: network + aca_env modules must be deployed first
################################################################################

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.14.0"
    }
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  subscription_id = var.subscription_id
}

# --- Data lookups: existing resources ---

data "azurerm_container_app_environment" "aca_env" {
  name                = var.aca_env_name
  resource_group_name = var.rg_app
}

data "azurerm_network_interface" "onprem_nic" {
  name                = "nic-onprem-sim"
  resource_group_name = var.rg_net
}

data "azurerm_storage_account" "storage" {
  name                = var.storage_account_name
  resource_group_name = var.rg_app
}

# --- Container App: On-prem Connectivity Test ---

resource "azurerm_container_app" "onprem_test" {
  name                         = var.app_onprem_name
  container_app_environment_id = data.azurerm_container_app_environment.aca_env.id
  resource_group_name          = var.rg_app
  revision_mode                = "Single"

  ingress {
    external_enabled = true  # external to ACA env (still private due to internal env)
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "onprem-test"
      image  = "alpine:3.19"
      cpu    = 0.25
      memory = "0.5Gi"

      command = ["/bin/sh", "-c"]
      args = [
        "apk add --no-cache curl busybox-extras; mkdir -p /tmp; echo 'HEALTH OK' > /tmp/index.html; (busybox httpd -f -p 0.0.0.0:8080 -h /tmp) & while true; do TS=$(date -Iseconds); for P in 80 443; do if (echo > /dev/tcp/${data.azurerm_network_interface.onprem_nic.private_ip_address}/$P) 2>/dev/null; then TCP=OK; else TCP=FAIL; fi; if curl -k -sS --max-time 3 --connect-timeout 2 http://${data.azurerm_network_interface.onprem_nic.private_ip_address}:$P >/dev/null 2>&1; then HTTP=OK; else HTTP=FAIL; fi; echo \"[$TS] onprem ${data.azurerm_network_interface.onprem_nic.private_ip_address} port $P TCP=$TCP HTTP=$HTTP\"; done; sleep 15; done"
      ]
    }
  }
}

# --- Container App: Private Endpoint Storage Test ---

resource "azurerm_container_app" "pe_storage_test" {
  name                         = var.app_pe_storage_name
  container_app_environment_id = data.azurerm_container_app_environment.aca_env.id
  resource_group_name          = var.rg_app
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = true  # external to ACA env (still private due to internal env)
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "pe-storage-test"
      image  = "alpine:3.19"
      cpu    = 0.25
      memory = "0.5Gi"

      command = ["/bin/sh", "-c"]
      args = [
        "apk add --no-cache curl jq bind-tools busybox-extras; mkdir -p /tmp; echo 'HEALTH OK' > /tmp/index.html; (busybox httpd -f -p 0.0.0.0:8080 -h /tmp) & get_token() { curl -sS -H \"X-IDENTITY-HEADER: $IDENTITY_HEADER\" \"$IDENTITY_ENDPOINT?api-version=2019-08-01&resource=$1\" | jq -r '.access_token'; }; resolve_host() { nslookup $1 2>/dev/null | awk '/Address/ {print $2}' | tail -n1 || getent hosts $1 | awk '{print $1}'; }; ST_FQDN=${var.storage_account_name}.blob.core.windows.net; while true; do TS=$(date -Iseconds); ST_PRIV_IP=$(resolve_host $ST_FQDN); ST_TOKEN=$(get_token https://storage.azure.com/); ST_RSP=$(curl -sS -X GET -H \"Authorization: Bearer $ST_TOKEN\" -H 'x-ms-version: 2021-08-06' \"https://$ST_FQDN/${var.storage_container_name}?restype=container&comp=list\" 2>&1); RSP_LEN=$(echo $ST_RSP | wc -c); echo \"[$TS] blob FQDN=$ST_FQDN privIP=$ST_PRIV_IP list_result_len=$RSP_LEN\"; sleep 30; done"
      ]
    }
  }
}

# --- RBAC: Storage Blob Data Reader for the PE Storage Test App ---

resource "azurerm_role_assignment" "pe_storage_test_blob_reader" {
  scope                = data.azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_container_app.pe_storage_test.identity[0].principal_id
}

# --- Data lookups: ACR and Managed Identity for ACR pull ---

data "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.rg_app
}

data "azurerm_user_assigned_identity" "aca_acr_pull" {
  name                = "id-aca-acr-pull"
  resource_group_name = var.rg_app
}

# --- Container App: File Upload App ---

resource "azurerm_container_app" "file_upload" {
  name                         = var.app_file_upload_name
  container_app_environment_id = data.azurerm_container_app_environment.aca_env.id
  resource_group_name          = var.rg_app
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [data.azurerm_user_assigned_identity.aca_acr_pull.id]
  }

  registry {
    server   = data.azurerm_container_registry.acr.login_server
    identity = data.azurerm_user_assigned_identity.aca_acr_pull.id
  }

  ingress {
    external_enabled = true 
    target_port      = 8080
    transport        = "auto"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "file-upload-app"
      image  = "${data.azurerm_container_registry.acr.login_server}/${var.file_upload_image_name}:${var.file_upload_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "PORT"
        value = "8080"
      }

      env {
        name  = "UPLOAD_FOLDER"
        value = "/app/uploads"
      }

      env {
        name  = "MAX_CONTENT_LENGTH"
        value = "16777216"  # 16MB
      }
    }
  }
}
