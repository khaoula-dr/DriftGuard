#!/usr/bin/env bash
# Tests des permissions effectives de drift-reader et drift-fixer (US-5)
# Les actions destructrices sont testées en --dry-run : AWS évalue les droits
# sans rien exécuter. "UnauthorizedOperation" = refus attendu.
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
export AWS_DEFAULT_REGION=eu-north-1

ACCOUNT="$(aws sts get-caller-identity --query Account --output text 2>/dev/null)" || {
  echo "ERREUR : session AWS invalide ou expirée. Relancez « aws login »." >&2; exit 2; }

INSTANCE="$(terraform -chdir="$REPO/terraform" output -raw instance_id)"
SG="$(terraform -chdir="$REPO/terraform" output -raw security_group_id)"
BUCKET="$(terraform -chdir="$REPO/terraform" output -raw app_bucket)"
TMP="$(mktemp)"; TAGS_JSON="$(mktemp)"
trap 'rm -f "$TMP" "$TAGS_JSON"' EXIT

assume() {  # $1 = nom du rôle ; exporte les identifiants temporaires (sous-shell)
  local creds
  creds="$(aws sts assume-role --role-arn "arn:aws:iam::${ACCOUNT}:role/$1" \
    --role-session-name "test-$1" \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)" || return 1
  read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<< "$creds"
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
}

fail() { echo "FAIL  $1"; [ -n "${2:-}" ] && echo "$2" | grep -iE "error|denied|not authorized" | head -n 3 | sed 's/^/        /'; echo x >> "$TMP"; }

denied() {   # refus AWS attendu
  local label="$1"; shift; local out
  out="$("$@" 2>&1)"
  if echo "$out" | grep -qiE "UnauthorizedOperation|AccessDenied|not authorized to perform"; then
    echo "PASS  refusé comme attendu : $label"
  else
    fail "non refusé : $label" "$out"
  fi
}

allowed() {  # la commande réelle doit réussir
  local label="$1"; shift; local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -eq 0 ]; then echo "PASS  autorisé comme attendu : $label"; else fail "échec : $label" "$out"; fi
}

dryrun_ok() {  # en --dry-run, "DryRunOperation" = l'action aurait été autorisée
  local label="$1"; shift; local out
  out="$("$@" 2>&1)"
  if echo "$out" | grep -q "DryRunOperation"; then
    echo "PASS  autorisé comme attendu : $label"
  else
    fail "échec : $label" "$out"
  fi
}

echo "=== drift-fixer (correction automatique : tags seulement) ==="
(
  assume drift-fixer || { fail "impossible d'assumer drift-fixer"; exit 0; }
  denied    "N1 suppression d'une instance"                  aws ec2 terminate-instances --instance-ids "$INSTANCE" --dry-run
  denied    "N2 modification d'un Security Group"            aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr 203.0.113.1/32 --dry-run
  denied    "N5 (bonus) tag hors des clés gérées"            aws ec2 create-tags --resources "$INSTANCE" --tags Key=Rogue,Value=1 --dry-run
  dryrun_ok "P2 écriture d'un tag autorisé sur l'instance"   aws ec2 create-tags --resources "$INSTANCE" --tags Key=Environment,Value=lab --dry-run
  if aws s3api get-bucket-tagging --bucket "$BUCKET" --output json > "$TAGS_JSON" 2>/dev/null; then
    allowed "P3 écriture des tags du bucket (mêmes valeurs)" aws s3api put-bucket-tagging --bucket "$BUCKET" --tagging "file://$TAGS_JSON"
  else
    fail "P3 lecture des tags du bucket impossible"
  fi
)

echo
echo "=== drift-reader (détection : lecture seule) ==="
(
  assume drift-reader || { fail "impossible d'assumer drift-reader"; exit 0; }
  denied  "N3 écriture sur une ressource métier"             aws ec2 create-tags --resources "$INSTANCE" --tags Key=Test,Value=1 --dry-run
  denied  "N4 document SSM non autorisé (AWS-RunShellScript)" aws ssm send-command --document-name AWS-RunShellScript --instance-ids "$INSTANCE" --parameters 'commands=["echo non"]'
  allowed "P1 lecture de l'instance"                         aws ec2 describe-instances --instance-ids "$INSTANCE"
  allowed "P4 lecture CloudTrail"                            aws cloudtrail lookup-events --max-results 1
  allowed "P5 lecture des tags du bucket"                    aws s3api get-bucket-tagging --bucket "$BUCKET"
  allowed "P6 document SSM autorisé (driftguard-check)"      aws ssm send-command --document-name driftguard-check --instance-ids "$INSTANCE"
  allowed "P7 terraform plan en lecture seule (-lock=false)" terraform -chdir="$REPO/terraform" plan -lock=false -input=false -no-color -detailed-exitcode
)

echo
if [ -s "$TMP" ]; then echo "RÉSULTAT : au moins un test est non conforme."; exit 1
else echo "RÉSULTAT : tous les tests sont conformes."; fi
