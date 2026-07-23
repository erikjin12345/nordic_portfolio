output "resource_group_name" {
  description = "Azure resource group."
  value       = azurerm_resource_group.this.name
}

output "vm_name" {
  description = "Portfolio worker VM."
  value       = azurerm_linux_virtual_machine.this.name
}

output "public_ip_address" {
  description = "VM public IP. Inbound access remains blocked unless admin_cidr is set."
  value       = azurerm_public_ip.this.ip_address
}

output "key_vault_name" {
  description = "Key Vault name used by the secret helper."
  value       = azurerm_key_vault.this.name
}

output "key_vault_uri" {
  description = "Key Vault data-plane URI."
  value       = azurerm_key_vault.this.vault_uri
}

output "ssh_command" {
  description = "SSH command when admin_cidr permits access."
  value       = "ssh -i ${trimsuffix(var.ssh_public_key_path, ".pub")} ${var.admin_username}@${azurerm_public_ip.this.ip_address}"
}

output "run_command_example" {
  description = "Inspect the timer without opening SSH."
  value       = "az vm run-command invoke -g ${azurerm_resource_group.this.name} -n ${azurerm_linux_virtual_machine.this.name} --command-id RunShellScript --scripts 'systemctl list-timers nordic-portfolio.timer --no-pager'"
}

output "backup_enabled" {
  description = "Whether daily VM backup is configured."
  value       = var.enable_backup
}
