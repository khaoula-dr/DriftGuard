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
## Bilan du Sprint 1

- **Livré** : 15 points sur 15 (US-1 à US-5), plus le bucket de state dédié (ADR-004).
- **Contraintes du compte** : la SCP n'a bloqué aucune des fonctions testées (rôles IAM, S3, SSM, CloudTrail, backend S3). Les stories repoussables (US-9, US-14) restent donc dans le Sprint 2 et 3.
- **Bon à garder** : tester les permissions avec des `--dry-run`, et écrire des garde-fous qui échouent si les droits d'un rôle sont élargis.
- **Surprises** : mon premier audit affichait « propre » alors que la session AWS avait expiré, et le contrôle de secrets de la CI se détectait lui-même. Dans les deux cas, un contrôle doit prouver qu'il sait échouer.
- **Pour le Sprint 2** : les 15 points restent réalistes ; l'identifiant d'acteur CloudTrail est un identifiant Identity Center, à traduire dans le rapport.
## Sprint 2 : US-6, observations sur le plan Terraform (2026-10-12)

- `resource_drift` est bien renseigné : tag `Environment` passé de `lab` à `prod` sur l'instance, modifié à la main.
- **Bruit** : `aws_iam_role.reader` apparaît en dérive à cause de l'attribut calculé `inline_policy` du rôle (cause probable : attribut non rafraîchi quand la politique est modifiée par la ressource `aws_iam_role_policy`). Exclu, car la politique reste suivie par `aws_iam_role_policy`. `tags_all` doublonne `tags` : exclu aussi.
- **Précision sur la section 4.2 du cahier des charges** : `resource_changes` contient aussi l'action qui ramène la ressource au code. Une dérive se reconnaît à sa présence dans `resource_drift` ; un changement de code non appliqué est une action de `resource_changes` sans dérive correspondante.
- **CloudTrail** : `lookup-events` remonte aussi les tentatives refusées et les `--dry-run` des tests IAM (sessions `test-drift-reader`, `test-drift-fixer`). L'attribution (US-10) devra lire `CloudTrailEvent` : ignorer les événements avec `errorCode`, comparer clé et valeur du tag, et borner la fenêtre de temps.
- Le script `drift.py check` assume `drift-reader` (jamais l'identité opérateur), vérifie le commit Git, écrit un rapport JSON dans `reports/` (non versionné) et masque `user_data`.

## Résultat US-5 (2026-10-11)

- Tests négatifs : 4 sur 4 refusés par AWS (+1 bonus : tag hors des clés gérées).
- Tests positifs : 7 sur 7 réussis.
- Le test P7 (`terraform plan` en lecture seule avec drift-reader) a d'abord échoué : permission `ssm:DescribeDocumentPermission` manquante. Ajoutée en lecture seule, sans élargir les droits d'écriture.

## Sprint 1 : US-4, CI GitHub

- `.github/workflows/ci.yml` : 4 jobs sans accès AWS (Terraform fmt et validate, ansible-lint, tests Python, détection de secrets).
- `tests/test_garde_fous_iam.py` : garde-fous statiques qui échouent si les droits de drift-reader ou drift-fixer sont élargis par erreur.
- `ansible/playbook.yml` : playbook minimal, étendu en US-8 et US-15.

## Sprint 2 : US-7, règles de classification

- Règles dans `driftguard/rules.py`, tableau lisible dans `docs/rules.md`.
- Décision : le tag `Project` n'est jamais corrigé automatiquement, car il intervient dans les conditions IAM de `drift-fixer` et de `drift-reader` (SendCommand). Conséquence cohérente : si `Project` est modifié, `drift-fixer` perd de toute façon le droit de taguer la ressource.
- Les actions de suppression ou de remplacement proposées par le plan produisent des alertes, jamais une correction.
- Observation : un `up.sh` a remplacé l'instance EC2 (1 ajoutée, 1 détruite), cause probable : la source de données AMI « dernière version » a changé. Un tel remplacement est exactement ce que la classe « Risque élevé » doit signaler.
