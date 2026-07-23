#!/usr/bin/env bash
set -euo pipefail

missing=()

for tool in git terraform az make jq; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    missing+=("${tool}")
  fi
done

if ((${#missing[@]} > 0)); then
  printf 'Missing required tools: %s\n' "${missing[*]}" >&2
  printf 'On macOS, install them with Homebrew before continuing.\n' >&2
  exit 1
fi

printf 'git:      %s\n' "$(git --version)"
printf 'terraform: %s\n' "$(terraform version -json | jq -r .terraform_version)"
printf 'azure-cli: %s\n' "$(az version | jq -r '."azure-cli"')"
printf 'jq:       %s\n' "$(jq --version)"
