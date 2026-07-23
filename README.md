# Nordic Portfolio – Azure-infrastruktur

Det här repot innehåller en säker, liten Azure-miljö för att köra ett
containeriserat portföljjobb enligt ett schema. Lösningen skapar:

- en Ubuntu-VM i `swedencentral`;
- ett privat virtuellt nätverk och en NSG som nekar inkommande trafik;
- valfri SSH-åtkomst från exakt ett administratörsnät;
- en systemtilldelad Managed Identity;
- Azure Key Vault med RBAC;
- en systemd-timer som kör containern utan root-behörigheter eller skrivbar
  root-filsystemsyta;
- beständig lokal lagring under `/var/lib/nordic-portfolio`.
- daglig Azure Backup med sju dagars retention.

Inga Avanza-uppgifter eller andra hemligheter lagras i Terraform, Git eller på
VM-disk. Vid varje körning hämtar VM:n de uttryckligen konfigurerade
hemligheterna från Key Vault till en tillfällig fil i `/run`, och raderar den när
jobbet avslutas.

> Infrastrukturen möjliggör schemalagd körning. Repot innehåller även en lokal,
> strikt skrivskyddad Avanza-MCP för analys och återbalanseringsförslag; se
> [Avanza MCP-integrationen](docs/AVANZA_MCP.md). Verifiera med Avanza att den
> inofficiella integrationsmetoden är tillåten innan den används. Automatisk
> orderläggning ingår inte.

## Förutsättningar

På den lokala datorn behövs Git, Terraform, Azure CLI, Make och jq.

```bash
make check
make local-setup
```

`make local-setup` skapar en separat SSH-nyckel i
`~/.ssh/nordic_portfolio_azure_ed25519` om den saknas och skapar en ignorerad
`infra/terraform/terraform.tfvars` från exempelfilen. Den skriver aldrig privata
nycklar eller hemligheter i repot.

Logga sedan in och välj rätt Azure-prenumeration:

```bash
make azure-login
az account set --subscription "<subscription-id>"
az account show --output table
```

## Konfiguration

Redigera den lokala, Git-ignorerade filen
`infra/terraform/terraform.tfvars`:

```hcl
project_name        = "nordic-portfolio"
location            = "swedencentral"
admin_username      = "portfolioadmin"
ssh_public_key_path = "~/.ssh/nordic_portfolio_azure_ed25519.pub"
container_image     = "ghcr.io/ditt-konto/nordic-portfolio:1.0.0"

# Sätt till din publika IP med /32 endast om direkt SSH behövs.
# Låt null vara kvar för helt stängd inkommande trafik.
admin_cidr = null

secret_mappings = {
  AVANZA_CREDENTIAL = "avanza-credential"
  NOTIFY_TOKEN      = "notify-token"
}
```

Använd en versionslåst image-tag, inte `latest`, i skarp drift. Image-registret
måste vara läsbart av VM:n; grundkonfigurationen förutsätter en publik image.

## Skapa infrastrukturen

```bash
make init
make validate
make plan
make apply
```

`apply` skapar resurser som kan medföra Azure-kostnader. Terraform state hålls
lokalt och ignoreras av Git. För teamdrift bör state flyttas till en separat,
låst Azure Storage-backend.

Efter apply:

```bash
make outputs
```

## Lägga in hemligheter

Lägg aldrig hemlighetsvärden i `terraform.tfvars`, `.env`, kommandoraden eller
Git. Följande kommando frågar efter värdet utan att visa det och skickar det
direkt till Key Vault:

```bash
make secret-set SECRET=avanza-credential
make secret-set SECRET=notify-token
```

Endast namn som finns i `secret_mappings` läses av VM-jobbet. Azure-identiteten
har bara rollen `Key Vault Secrets User`; den kan läsa men inte ändra
hemligheter.

## Drift

Timern aktiveras automatiskt. Inspektera den genom Azure Run Command eller,
om `admin_cidr` är satt, via SSH:

```bash
systemctl list-timers nordic-portfolio.timer
sudo systemctl start nordic-portfolio.service
sudo journalctl -u nordic-portfolio.service
```

Jobbet körs som standard söndag 08:00 svensk tid. Ändra `schedule` i den lokala
tfvars-filen och kör `make apply` igen för att ändra det.

Containern får:

- de valda Key Vault-värdena som miljövariabler;
- `PORTFOLIO_DATA_DIR=/data`;
- en beständig volym monterad på `/data`;
- endast utgående nätverksåtkomst;
- read-only root-filsystem, borttagna Linux capabilities och resursgränser.

Programmet bör själv implementera idempotens, maxbelopp, kontroll av orderstatus,
dry-run och manuell bekräftelse.

## Kostnads- och säkerhetsval

Standardstorleken är `Standard_B1s`. VM:n kör dygnet runt för att systemd-timern
ska fungera. Ingen databas, lastbalanserare, publik webbapp eller betald Bastion
skapas. Azure Backup är aktiverad som standard och medför en mindre separat
kostnad; sätt `enable_backup = false` om du uttryckligen vill avstå.

Key Vault har soft delete och purge protection. `terraform destroy` kan därför
inte omedelbart radera valvet permanent, vilket är avsiktligt.

## Ta bort resurser

Granska alltid planen först:

```bash
make plan-destroy
make destroy
```

Detta tar bort VM, nätverk och övriga resurser i resource group, men Key Vault
kan ligga kvar som soft-deleted under retentionperioden.
