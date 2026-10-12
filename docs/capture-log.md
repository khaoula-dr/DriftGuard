# Journal des captures

Fichiers dans `docs/media/` (images .png). Les vidéos restent hors de Git.
Avant publication : masquer l'identifiant de compte AWS (12 chiffres), les ARN et tout jeton.

| Jalon | Capture | Fichier | Fait |
|---|---|---|---|
| US-1/US-2 | Résultat de terraform apply (« Apply complete ») | 01-apply.png | |
| US-1/US-2 | Instance « Online » dans SSM + aucun port entrant dans le Security Group | 02-ssm-online.png | |
| US-1/US-2 | Nginx répond 200 via SSM | 03-nginx-200.png | |
| US-3 | Audit propre après destroy (« AUDIT PROPRE ») | 04-audit-propre.png | |
| Sprint 2 | Plan Terraform montrant "Environment" = "prod" -> "lab" (cadrer sans les lignes du compte) | 08-plan-derive.png | |
| US-6 | Sortie de drift.py check avec la dérive détectée | 09-drift-check.png | |
| US-6 | Extrait du rapport : jq '.drifts' reports/<fichier>.json | 10-rapport-json.png | |
