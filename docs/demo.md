# Démonstration : commandes à rejouer

Prérequis : infrastructure déployée (`./scripts/up.sh`) et session AWS valide (`aws login`).

## Scénario 1 : tag modifié à la main

```bash
# Injecter la dérive (hors Terraform)
aws ec2 create-tags --resources $(terraform -chdir=terraform output -raw instance_id) \
  --tags Key=Environment,Value=prod

# Détecter
python3 drift.py check
```
Attendu : `tags.Environment : "lab" -> "prod"` classé Métadonnées / faible / `auto_fix`.
Les scénarios suivants (correction, attribution) seront complétés avec US-10 et US-11.

## Scénario 3 : correction qui échoue

À compléter avec US-13 (arrêt à la première erreur).

## Scénario 4 : suppression tentée avec drift-fixer (final)

```bash
(
  ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
  read -r AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN <<< "$(aws sts assume-role \
    --role-arn arn:aws:iam::${ACCOUNT}:role/drift-fixer --role-session-name demo \
    --query 'Credentials.[AccessKeyId,SecretAccessKey,SessionToken]' --output text)"
  export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  aws ec2 terminate-instances --region eu-north-1 \
    --instance-ids $(terraform -chdir=terraform output -raw instance_id)
)
```
Attendu : `UnauthorizedOperation`. AWS refuse : `drift-fixer` n'a aucun droit de suppression.
(La tentative vise une ressource de laboratoire ; les tests `scripts/test_iam.sh` utilisent `--dry-run`.)
