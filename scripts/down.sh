#!/usr/bin/env bash
# Détruit l'infrastructure de laboratoire, puis audite les restes
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
(cd "$HERE/../terraform" && terraform destroy "$@")
"$HERE/audit.sh"
