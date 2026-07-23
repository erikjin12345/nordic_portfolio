#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tf_dir="${repo_root}/infra/terraform"
ssh_key="${HOME}/.ssh/nordic_portfolio_azure_ed25519"
tfvars="${tf_dir}/terraform.tfvars"

mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

if [[ ! -f "${ssh_key}" ]]; then
  ssh-keygen -t ed25519 -a 100 -f "${ssh_key}" -C "nordic-portfolio-azure" -N ""
  chmod 600 "${ssh_key}"
  chmod 644 "${ssh_key}.pub"
  printf 'Created SSH key: %s\n' "${ssh_key}"
else
  printf 'SSH key already exists: %s\n' "${ssh_key}"
fi

if [[ ! -f "${tfvars}" ]]; then
  cp "${tf_dir}/terraform.tfvars.example" "${tfvars}"
  chmod 600 "${tfvars}"
  printf 'Created local config: %s\n' "${tfvars}"
else
  printf 'Local config already exists: %s\n' "${tfvars}"
fi

if az account show >/dev/null 2>&1; then
  printf 'Azure CLI is authenticated.\n'
else
  printf 'Next step: run "make azure-login", then select the intended subscription.\n'
fi
