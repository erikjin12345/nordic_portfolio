variable "project_name" {
  description = "Short resource-name prefix."
  type        = string
  default     = "nordic-portfolio"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project_name))
    error_message = "project_name must be 3-20 lowercase alphanumeric/hyphen characters and start with a letter."
  }
}

variable "location" {
  description = "Azure region."
  type        = string
  default     = "swedencentral"
}

variable "admin_username" {
  description = "Linux administrator username."
  type        = string
  default     = "portfolioadmin"

  validation {
    condition     = can(regex("^[a-z_][a-z0-9_-]{0,30}$", var.admin_username))
    error_message = "admin_username must be a valid Linux username."
  }
}

variable "ssh_public_key_path" {
  description = "Local path to the SSH public key. The private key must never be committed."
  type        = string
  default     = "~/.ssh/nordic_portfolio_azure_ed25519.pub"
}

variable "admin_cidr" {
  description = "Optional single CIDR allowed to SSH. Keep null to deny all inbound traffic."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.admin_cidr == null || can(cidrhost(var.admin_cidr, 0))
    error_message = "admin_cidr must be null or a valid CIDR, preferably your public IP with /32."
  }
}

variable "vm_size" {
  description = "Azure VM SKU."
  type        = string
  default     = "Standard_B1s"
}

variable "container_image" {
  description = "Public, version-pinned OCI image containing the portfolio job."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9._/-]+:[A-Za-z0-9._-]+$", var.container_image)) && !endswith(var.container_image, ":latest")
    error_message = "container_image must include a versioned tag; :latest is not permitted."
  }
}

variable "schedule" {
  description = "systemd OnCalendar expression including timezone."
  type        = string
  default     = "Sun *-*-* 08:00:00 Europe/Stockholm"

  validation {
    condition     = can(regex("^[A-Za-z0-9*,:/._ -]{5,100}$", var.schedule))
    error_message = "schedule contains unsupported characters."
  }
}

variable "secret_mappings" {
  description = "Map of container environment-variable names to Key Vault secret names. Values, never secrets themselves, are committed/configured here."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for env_name, secret_name in var.secret_mappings :
      can(regex("^[A-Z][A-Z0-9_]{0,63}$", env_name)) &&
      can(regex("^[0-9A-Za-z-]{1,127}$", secret_name))
    ])
    error_message = "Environment names must be uppercase identifiers and Key Vault names may contain letters, digits, and hyphens."
  }
}

variable "job_timeout_seconds" {
  description = "Maximum total runtime for one portfolio job."
  type        = number
  default     = 900

  validation {
    condition     = var.job_timeout_seconds >= 60 && var.job_timeout_seconds <= 3600
    error_message = "job_timeout_seconds must be between 60 and 3600."
  }
}

variable "container_memory" {
  description = "Docker memory limit."
  type        = string
  default     = "512m"

  validation {
    condition     = can(regex("^[1-9][0-9]*(m|g)$", var.container_memory))
    error_message = "container_memory must look like 512m or 1g."
  }
}

variable "enable_backup" {
  description = "Enable daily Azure Backup for the VM with seven days of retention."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional Azure resource tags."
  type        = map(string)
  default     = {}
}
