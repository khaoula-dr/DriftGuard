# Journal des captures

Fichiers dans `docs/media/` (images .png). Les vidéos restent hors de Git.
Avant publication : masquer l'identifiant de compte AWS (12 chiffres), les ARN et tout jeton.

| Jalon | Capture | Fichier | Fait |
|---|---|---|---|
| US-1/US-2 | Résultat de terraform apply (« Apply complete ») | 01-apply.png | |
| US-1/US-2 | Instance « Online » dans SSM + aucun port entrant dans le Security Group | 02-ssm-online.png | |
| US-1/US-2 | Nginx répond 200 via SSM | 03-nginx-200.png | |
| US-3 | Audit propre après destroy (« AUDIT PROPRE ») | 04-audit-propre.png | |
| US-5 | Écran complet de scripts/test_iam.sh, tout en PASS | 05-tests-iam.png | |
| US-5 | Politique JSON de drift-fixer dans la console IAM (flouter le compte) | 06-politique-fixer.png | |
| US-4 | CI verte sur GitHub (pull request, 4 jobs) | 07-ci-verte.png | |
