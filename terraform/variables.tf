variable "subscription_id" {
  description = "id of the subscription"
  type        = string
}


variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "resource_group_location" {
  description = "Location of the resource group"
  type        = string
}

variable "aks_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "dns_prefix" {
  description = "DNS prefix for AKS cluster"
  type        = string
}

variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
}

variable "vm_size" {
  description = "VM size for the AKS nodes"
  type        = string
}

variable "os_disk_size_gb" {
  description = "OS disk size for the nodes"
  type        = number
}
