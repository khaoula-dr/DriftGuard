#!/usr/bin/env bash
# Vérifie qu'il ne reste aucune ressource du projet (tag Project=driftguard)
# Codes de sortie : 0 = propre, 1 = restes trouvés, 2 = audit impossible (erreur AWS)
REGION="${AWS_REGION:-eu-north-1}"
FOUND=0
ERROR=0

# Pré-vérification : sans session valide, l'audit ne prouve rien
if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  echo "ERREUR : session AWS invalide ou expirée. Relancez « aws login » puis l'audit." >&2
  exit 2
fi

check() {  # $1 = libellé, puis la commande AWS à exécuter
  local label="$1"; shift
  local out rc
  out="$("$@" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ]; then
    if echo "$out" | grep -q "NoSuchEntity"; then
      echo "OK     $label"                      # la ressource n'existe pas : normal
    else
      echo "ERREUR $label : $(echo "$out" | head -n 1)"; ERROR=1
    fi
  elif [ -n "$out" ] && [ "$out" != "None" ]; then
    echo "RESTE  $label : $out"; FOUND=1
  else
    echo "OK     $label"
  fi
}

check "instances EC2" aws ec2 describe-instances --region "$REGION" \
  --filters Name=tag:Project,Values=driftguard \
            Name=instance-state-name,Values=pending,running,stopping,stopped \
  --query 'Reservations[].Instances[].InstanceId' --output text

check "security groups" aws ec2 describe-security-groups --region "$REGION" \
  --filters Name=tag:Project,Values=driftguard \
  --query 'SecurityGroups[].GroupId' --output text

check "buckets S3" aws resourcegroupstaggingapi get-resources --region "$REGION" \
  --resource-type-filters s3 --tag-filters Key=Project,Values=driftguard \
  --query 'ResourceTagMappingList[].ResourceARN' --output text

check "rôle IAM" aws iam get-role --role-name driftguard-ec2 \
  --query Role.RoleName --output text

check "profil d'instance" aws iam get-instance-profile \
  --instance-profile-name driftguard-ec2 \
  --query InstanceProfile.InstanceProfileName --output text

if [ "$ERROR" -eq 1 ]; then
  echo "AUDIT INCOMPLET : au moins une vérification a échoué (voir ERREUR)."
  exit 2
elif [ "$FOUND" -eq 1 ]; then
  echo "AUDIT : des restes existent."
  exit 1
else
  echo "AUDIT PROPRE : aucun reste."
  exit 0
fi