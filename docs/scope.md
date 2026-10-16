# Périmètre révisé (2026-10-12)

## Énoncé du projet

DriftGuard détecte quand une infrastructure AWS s'écarte de Git (Terraform), retrouve l'événement
CloudTrail qui l'explique, et ne corrige automatiquement que ce qu'une politique IAM l'empêche de casser.

**Extension prévue** : détection de la dérive de configuration d'un serveur (Ansible via SSM), voir ADR-005.

## Stories

| Story | Pts | Périmètre |
|---|---|---|
| US-1 à US-7 | 23 | Retenu |
| US-10 attribution CloudTrail | 2 | Retenu |
| US-11 correction des tags | 3 | Retenu |
| US-12 confirmation manuelle | 3 | Retenu |
| US-13 arrêt à la première erreur | 3 | Retenu |
| US-16 mesures | 2 | Retenu |
| US-17 README, ADR, démo, nettoyage | 3 | Retenu |
| US-8 Ansible en mode check via SSM | 3 | Reportée (extension prévue) |
| US-9 scripts d'injection de dérive | 2 | Remplacée par des commandes documentées (`docs/demo.md`) |
| US-14 vérification HTTP 200 | 2 | Reportée (la vérification par nouveau `check` reste dans US-11) |
| US-15 playbook de remédiation Ansible | 3 | Reportée (extension prévue) |

Total retenu : 39 points. Reporté : 10 points.

## Démonstration

Trois scénarios : tag modifié à la main (détection, attribution, correction automatique),
correction qui échoue (arrêt à la première erreur), suppression tentée avec `drift-fixer` refusée par AWS (final).
Les commandes d'injection sont dans `docs/demo.md`.
