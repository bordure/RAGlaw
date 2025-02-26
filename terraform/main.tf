terraform {
  required_version = "~> 1.10.5"
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}


resource "azurerm_resource_group" "law-rag-model-rg" {
  name     = var.resource_group_name
  location = var.resource_group_location
}

resource "azurerm_kubernetes_cluster" "law-rag-model-aks" {
  name                = var.aks_name
  location            = azurerm_resource_group.law-rag-model-rg.location
  resource_group_name = azurerm_resource_group.law-rag-model-rg.name
  dns_prefix          = var.dns_prefix

  default_node_pool {
    name            = "default"
    node_count      = var.node_count
    vm_size         = var.vm_size
    os_disk_size_gb = var.os_disk_size_gb
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "basic"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    Environment = "Development"
  }
}

