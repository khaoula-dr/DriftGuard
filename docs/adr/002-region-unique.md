# ADR-002 : Région unique eu-north-1

- **Contexte** : les autres régions sont bloquées par une SCP.
- **Options étudiées** : multi-région (bloqué, hors périmètre).
- **Décision** : tout le projet vit dans eu-north-1.
- **Conséquences** : les événements IAM globaux ne sont pas visibles dans cette région ; sans effet sur les ressources surveillées (EC2, S3, Security Group, tags).
- **Validation** : apply réussi dans eu-north-1 (2026-10-11).
