#!/usr/bin/env bash
# Déploie l'infrastructure de laboratoire
set -euo pipefail
cd "$(dirname "$0")/../terraform"
terraform init -input=false
terraform apply "$@"
