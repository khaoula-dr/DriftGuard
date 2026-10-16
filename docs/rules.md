# Règles de classification

Centralisées dans `driftguard/rules.py`, testées sans AWS (`tests/test_rules.py`).

| Écart | Classe | Risque | Action |
|---|---|---|---|
| Tag géré (Environment, ManagedBy) modifié ou manquant, sur instance, Security Group ou bucket | Métadonnées | faible | Correction automatique (drift-fixer) après revérification |
| Tag `Project` modifié (intervient dans des politiques IAM et SSM) | À analyser | élevé | Confirmation manuelle |
| Tag hors des clés gérées, ajouté ou retiré à la main | À analyser | moyen | Confirmation manuelle |
| Propriété d'un Security Group, d'un rôle ou d'une politique IAM | Réseau et sécurité | élevé | Alerte et confirmation manuelle |
| Autre propriété d'une instance ou d'un bucket | Infrastructure | moyen | Alerte et confirmation manuelle |
| Fichier de configuration Nginx modifié | Système | moyen | Détection, puis correction Ansible après confirmation |
| Ressource supprimée hors Terraform, ou suppression proposée par le plan | Destructive | critique | Alerte seule, jamais automatique |
| Remplacement proposé par le plan | Risque élevé | élevé | Alerte seule, jamais automatique |
| Erreur pendant la détection ou la correction | Indéterminé | n/a | Arrêt immédiat, diagnostic sauvegardé |

Principe : la correction automatique n'est ouverte qu'aux tags gérés, non sensibles, sur un type de ressource
que `drift-fixer` a le droit de taguer. Le test `test_auto_fix_reserve_aux_tags_geres` le garantit.
