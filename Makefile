SHELL := /bin/bash
TF_DIR := infra/terraform
TF := terraform -chdir=$(TF_DIR)

.PHONY: check local-setup azure-login init fmt validate plan apply outputs \
	secret-set plan-destroy destroy

check:
	@./scripts/check-prereqs.sh

local-setup: check
	@./scripts/local-setup.sh

azure-login:
	@az login

init:
	@$(TF) init

fmt:
	@terraform fmt -recursive

validate: fmt
	@$(TF) validate

plan:
	@$(TF) plan -out=nordic-portfolio.tfplan

apply:
	@$(TF) apply nordic-portfolio.tfplan

outputs:
	@$(TF) output

secret-set:
	@test -n "$(SECRET)" || (echo "Usage: make secret-set SECRET=<key-vault-secret-name>" >&2; exit 2)
	@./scripts/set-key-vault-secret.sh "$(SECRET)"

plan-destroy:
	@$(TF) plan -destroy

destroy:
	@$(TF) destroy
