data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  resource_prefix = "${var.project_name}-${random_string.suffix.result}"
  key_vault_name  = "${substr(replace(var.project_name, "-", ""), 0, 14)}-${random_string.suffix.result}"
  common_tags = merge(
    {
      application = var.project_name
      managed-by  = "terraform"
      workload    = "portfolio-rebalancer"
    },
    var.tags
  )
  secret_mappings = join("\n", [
    for env_name, secret_name in var.secret_mappings : "${env_name}=${secret_name}"
  ])
}

resource "azurerm_resource_group" "this" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

resource "azurerm_virtual_network" "this" {
  name                = "${local.resource_prefix}-vnet"
  address_space       = ["10.20.0.0/16"]
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.common_tags
}

resource "azurerm_subnet" "workload" {
  name                 = "workload"
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = ["10.20.1.0/24"]
  service_endpoints    = ["Microsoft.KeyVault"]
}

resource "azurerm_network_security_group" "this" {
  name                = "${local.resource_prefix}-nsg"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.common_tags
}

resource "azurerm_network_security_rule" "ssh" {
  count = var.admin_cidr == null ? 0 : 1

  name                        = "AllowSshFromAdmin"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "22"
  source_address_prefix       = var.admin_cidr
  destination_address_prefix  = "*"
  resource_group_name         = azurerm_resource_group.this.name
  network_security_group_name = azurerm_network_security_group.this.name
}

resource "azurerm_public_ip" "this" {
  name                = "${local.resource_prefix}-pip"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = local.common_tags
}

resource "azurerm_network_interface" "this" {
  name                = "${local.resource_prefix}-nic"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  tags                = local.common_tags

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.workload.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.this.id
  }
}

resource "azurerm_network_interface_security_group_association" "this" {
  network_interface_id      = azurerm_network_interface.this.id
  network_security_group_id = azurerm_network_security_group.this.id
}

resource "azurerm_key_vault" "this" {
  name                       = local.key_vault_name
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 30
  tags                       = local.common_tags
}

resource "azurerm_linux_virtual_machine" "this" {
  name                            = "${local.resource_prefix}-vm"
  computer_name                   = "portfolio-worker"
  location                        = azurerm_resource_group.this.location
  resource_group_name             = azurerm_resource_group.this.name
  size                            = var.vm_size
  admin_username                  = var.admin_username
  disable_password_authentication = true
  network_interface_ids           = [azurerm_network_interface.this.id]
  encryption_at_host_enabled      = false
  tags                            = local.common_tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(pathexpand(var.ssh_public_key_path))
  }

  identity {
    type = "SystemAssigned"
  }

  os_disk {
    name                 = "${local.resource_prefix}-osdisk"
    caching              = "ReadWrite"
    storage_account_type = "StandardSSD_LRS"
    disk_size_gb         = 30
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  boot_diagnostics {}

  custom_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
    admin_username      = var.admin_username
    container_image     = var.container_image
    container_memory    = var.container_memory
    job_timeout_seconds = var.job_timeout_seconds
    key_vault_uri       = azurerm_key_vault.this.vault_uri
    schedule            = var.schedule
    secret_mappings     = local.secret_mappings
  }))

  depends_on = [
    azurerm_network_interface_security_group_association.this
  ]
}

resource "azurerm_role_assignment" "vm_secret_reader" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_virtual_machine.this.identity[0].principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "deployer_secret_officer" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_recovery_services_vault" "this" {
  count = var.enable_backup ? 1 : 0

  name                = "${local.resource_prefix}-backup"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "Standard"
  tags                = local.common_tags
}

resource "azurerm_backup_policy_vm" "daily" {
  count = var.enable_backup ? 1 : 0

  name                = "daily-seven-days"
  resource_group_name = azurerm_resource_group.this.name
  recovery_vault_name = azurerm_recovery_services_vault.this[0].name
  timezone            = "UTC"

  backup {
    frequency = "Daily"
    time      = "02:00"
  }

  retention_daily {
    count = 7
  }
}

resource "azurerm_backup_protected_vm" "this" {
  count = var.enable_backup ? 1 : 0

  resource_group_name = azurerm_resource_group.this.name
  recovery_vault_name = azurerm_recovery_services_vault.this[0].name
  source_vm_id        = azurerm_linux_virtual_machine.this.id
  backup_policy_id    = azurerm_backup_policy_vm.daily[0].id
}
