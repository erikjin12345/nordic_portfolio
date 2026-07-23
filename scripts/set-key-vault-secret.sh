#!/usr/bin/env bash
set -euo pipefail

if (($# != 1)); then
  printf 'Usage: %s <secret-name>\n' "$0" >&2
  exit 2
fi

secret_name="$1"
if [[ ! "${secret_name}" =~ ^[0-9A-Za-z-]{1,127}$ ]]; then
  printf 'Invalid Key Vault secret name.\n' >&2
  exit 2
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tf_dir="${repo_root}/infra/terraform"

if ! az account show >/dev/null 2>&1; then
  printf 'Azure CLI is not authenticated. Run "make azure-login" first.\n' >&2
  exit 1
fi

vault_name="$(terraform -chdir="${tf_dir}" output -raw key_vault_name 2>/dev/null || true)"
if [[ -z "${vault_name}" ]]; then
  printf 'No Terraform Key Vault output found. Run make apply first.\n' >&2
  exit 1
fi

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT
chmod 600 "${tmp_file}"

read -r -s -p "Value for ${secret_name}: " secret_value
printf '\n'
if [[ -z "${secret_value}" ]]; then
  printf 'Refusing to store an empty value.\n' >&2
  exit 1
fi
printf '%s' "${secret_value}" >"${tmp_file}"
unset secret_value

az keyvault secret set \
  --vault-name "${vault_name}" \
  --name "${secret_name}" \
  --file "${tmp_file}" \
  --only-show-errors \
  --output none

printf 'Stored secret "%s" in Key Vault "%s".\n' "${secret_name}" "${vault_name}"
