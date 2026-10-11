#!/usr/bin/env bash
# Déploie l'infrastructure de laboratoire
set -euo pipefail
cd "$(dirname "$0")/../terraform"
if [ -f backend.hcl ]; then
  terraform init -input=false -backend-config=backend.hcl
else
  terraform init -input=false
fi
terraform apply "$@"
