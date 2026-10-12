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

## Sprint 1 : US-3, scripts up et down

- `scripts/up.sh` : init puis apply ; `scripts/down.sh` : destroy puis audit ; `scripts/audit.sh` : cherche les restes par tag Project=driftguard (EC2, Security Groups, S3) et par nom (rôle et profil IAM).
- Le futur bucket de state aura un tag différent (Project=driftguard-state) pour rester hors du cycle de destruction (ADR-004).

## Sprint 1 : bucket de state dédié (ADR-004)

- `bootstrap/` : crée un bucket S3 dédié (versioning, chiffrement, accès public bloqué, `prevent_destroy`), tag `Project=driftguard-state` pour rester hors de l'audit et de `down.sh`.
- `terraform/versions.tf` : backend S3 avec `use_lockfile`, paramètres lus dans `backend.hcl` (non versionné, contient l'identifiant de compte ; modèle dans `backend.hcl.example`).

## Sprint 1 : US-5, identités IAM séparées

- `terraform/iam.tf` : `drift-reader` (lecture, CloudTrail, state sans verrou, SendCommand limité à un seul document SSM et aux instances taguées du projet) et `drift-fixer` (CreateTags et PutBucketTagging seulement, sur les ressources du projet et les clés de tags gérées).
- `scripts/test_iam.sh` : 4 tests négatifs obligatoires (+1 bonus) et tests positifs. Les actions destructrices sont testées en `--dry-run` : AWS évalue les droits sans rien exécuter.
- Limite documentée : les tests prouvent les permissions effectives dans les conditions testées, pas l'absence de tout risque.
- `scripts/audit.sh` étendu aux rôles `drift-reader`, `drift-fixer` et au document `driftguard-check`.

## Résultat US-5 (2026-10-11)

- Tests négatifs : 4 sur 4 refusés par AWS (+1 bonus : tag hors des clés gérées).
- Tests positifs : 7 sur 7 réussis.
- Le test P7 (`terraform plan` en lecture seule avec drift-reader) a d'abord échoué : permission `ssm:DescribeDocumentPermission` manquante. Ajoutée en lecture seule, sans élargir les droits d'écriture.

## Sprint 1 : US-4, CI GitHub

- `.github/workflows/ci.yml` : 4 jobs sans accès AWS (Terraform fmt et validate, ansible-lint, tests Python, détection de secrets).
- `tests/test_garde_fous_iam.py` : garde-fous statiques qui échouent si les droits de drift-reader ou drift-fixer sont élargis par erreur.
- `ansible/playbook.yml` : playbook minimal, étendu en US-8 et US-15.
