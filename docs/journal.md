# Journal de projet

## 2026-10-11 : Étape préalable, test des contraintes du compte

| Test | Résultat | Conséquence |
|---|---|---|
| Identité et région | Connexion via IAM Identity Center (rôle AccountFullAccessRole), région eu-north-1 | ADR-002 confirmé |
| CloudTrail lookup-events | Fonctionne ; événement CreateBucket retrouvé par nom de ressource | Attribution faisable (US-10) ; l'acteur est un identifiant Identity Center |
| Délai CloudTrail | Premier essai vide juste après l'apply, événement visible ensuite | État « pending » justifié |
| Terraform apply : rôle IAM, bucket S3, document SSM | Créés dans eu-north-1 | US-5 et US-8 faisables |
| Backend S3 avec use_lockfile | State écrit ; plan -lock=false sans erreur | ADR-004 validé |
| EC2 t3.micro sans port entrant + SSM | Instance « Online » ; send-command AWS-RunShellScript réussi | US-2 faisable, sans SSH |
| Destroy et vérification | Aucun reste | Procédure de nettoyage validée (US-3) |

À tester plus tard : exécution d'un document SSM personnalisé (US-8) et refus
d'un document non autorisé pour drift-reader (US-5).

## Sprint 1 : US-1 et US-2, socle Terraform

- Fichiers : `terraform/variables.tf`, `main.tf`, `outputs.tf`.
- Contenu : EC2 t3.micro (Amazon Linux 2023, Nginx, IMDSv2 obligatoire, disque chiffré), rôle SSM, Security Group sans règle entrante, bucket S3 privé, tags de référence (Project, Environment, ManagedBy).
- Choix : state local pour l'instant, migration vers le bucket dédié prévue (ADR-004).
